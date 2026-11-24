"""Resolve student CSV rows and plan enrollment and eligibility changes."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import func, or_, select, tuple_

from app.models import AcademicEdition, Enrollment, Subject, User, UserRole
from app.services.enrollment_access import enable_for_play


@dataclass(frozen=True)
class PlannedEnrollment:
    dni: str
    name: str
    email: str
    edition: AcademicEdition
    account: User | None
    enrollment: Enrollment | None
    enabled_edition_id: int | None


def inspect(db, rows, errors, row_numbers):
    destinations = {(code, year) for _, _, _, _, code, year in rows}
    editions = {
        (code, edition.academic_year): (edition, name)
        for edition, code, name in db.execute(
            select(AcademicEdition, Subject.code, Subject.name).join(Subject, AcademicEdition.subject_id == Subject.id)
            .where(tuple_(Subject.code, AcademicEdition.academic_year).in_(destinations))
        )
    }
    email_by_dni, dni_by_email, names_by_dni = defaultdict(set), defaultdict(set), defaultdict(set)
    requested_years = defaultdict(set)
    for _, dni, name, email, code, year in rows:
        email_by_dni[dni].add(email)
        dni_by_email[email].add(dni)
        names_by_dni[dni].add(name)
        requested_years[dni, code].add(year)

    users = db.scalars(select(User).where(
        or_(User.dni.in_(list(email_by_dni)), func.lower(User.email).in_(list(dni_by_email)))
    )).all()
    users_by_dni = {user.dni: user for user in users}
    users_by_email = defaultdict(list)
    for user in users:
        users_by_email[user.email.lower()].append(user)

    enrolled, active = {}, {}
    for enrollment, year in db.execute(select(Enrollment, AcademicEdition.academic_year)
        .join(AcademicEdition, AcademicEdition.id == Enrollment.edition_id)
        .where(
            Enrollment.student_id.in_([user.id for user in users]),
            Enrollment.subject_id.in_({edition.subject_id for edition, _ in editions.values()}),
            or_(Enrollment.play_enabled.is_(True),
                Enrollment.edition_id.in_({edition.id for edition, _ in editions.values()})),
        )
    ):
        enrolled[enrollment.student_id, enrollment.edition_id] = enrollment
        if enrollment.play_enabled:
            active[enrollment.student_id, enrollment.subject_id] = (enrollment.edition_id, year)

    duplicates = Counter((dni, code, year) for _, dni, _, _, code, year in rows)
    plan, preview = [], []
    first_new_account_row = {}
    first_account_row = {}
    for number, dni, name, email, code, year in rows:
        before = len(errors)

        def issue(field, message):
            errors.append({"row": number, "field": field, "message": message})

        destination = editions.get((code, year))
        if destination is None:
            issue("codigo_asignatura / anio_academico", "No existe esa edición. Comprueba el código y el año.")
        if len(email_by_dni[dni]) > 1 or len(dni_by_email[email]) > 1:
            issue("dni / correo", "El archivo asocia el DNI o correo a identidades distintas.")
        elif duplicates[dni, code, year] > 1:
            issue("matrícula", "Matrícula duplicada dentro del CSV.")
        if len(requested_years[dni, code]) > 1:
            issue("anio_academico", "Deja una sola fila con el curso que debe quedar habilitado para este alumno y asignatura.")

        user = users_by_dni.get(dni)
        matches = users_by_email[email]
        if (user is not None or matches) and (user is None or matches != [user]):
            issue("dni / correo", "El DNI y el correo no identifican de forma inequívoca a la misma cuenta.")
        elif user is not None and user.role != UserRole.STUDENT:
            issue("rol", "La cuenta existente no tiene rol de alumnado.")
        elif user is None and len(names_by_dni[dni]) > 1:
            issue("nombre", "Usa el mismo nombre en todas las filas de la cuenta nueva.")
        if len(errors) != before:
            continue

        edition, subject_name = destination
        existing = enrolled.get((user.id, edition.id)) if user is not None else None
        enabled_id, enabled_year = active.get((user.id, edition.subject_id), (None, None)) if user else (None, None)
        if user is None:
            action = "new_account"
        elif existing is None:
            action = "new_enrollment"
        else:
            action = "existing_enrollment"
        name = user.name if user else name
        if user is None:
            first_new_account_row.setdefault(dni, number)
        preview.append({
            "row": number, "dni": "••••••" + dni[-3:], "name": name, "email": email,
            "edition_id": edition.id, "previous_edition_id": enabled_id,
            "account_row": first_account_row.setdefault(dni, number),
            "subject_code": code, "subject_name": subject_name, "academic_year": year, "action": action,
            "previous_year": enabled_year, "enabled_year": year,
        })
        plan.append(PlannedEnrollment(dni, name, email, edition, user, existing, enabled_id))

    has_changes = any(row.enrollment is None or row.enabled_edition_id != row.edition.id for row in plan)
    return plan, {"has_changes": has_changes,"total": len(row_numbers), "valid": len(preview), "errors": sorted(errors, key=lambda error: error["row"]),
                  "preview": preview, "summary": {
                      "new_accounts": len(first_new_account_row),
                      "new_enrollments": sum(row.enrollment is None for row in plan),
                      "year_changes": sum(row["previous_year"] is not None and row["previous_year"] != row["enabled_year"]
                                          for row in preview),
                  }}


def apply(db, plan):
    new_accounts = {}
    for row in plan:
        if row.account is None and row.dni not in new_accounts:
            new_accounts[row.dni] = User(dni=row.dni, name=row.name, email=row.email, role=UserRole.STUDENT)
    if new_accounts:
        db.add_all(new_accounts.values())
        db.flush()

    targets, added = [], 0
    for row in plan:
        target = row.enrollment
        if target is None:
            account = row.account or new_accounts[row.dni]
            target = Enrollment(student_id=account.id, subject_id=row.edition.subject_id,
                                edition_id=row.edition.id, play_enabled=False)
            db.add(target)
            added += 1
        targets.append(target)
    db.flush()
    for target in targets:
        enable_for_play(db, target)
    return list(new_accounts.values()), added, len(plan) - added
