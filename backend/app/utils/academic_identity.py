import re


def normalize_subject_code(value: str) -> str:
    code = value.strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9_-]{0,31}", code):
        raise ValueError("Indica un código de asignatura con letras A–Z, números, guion o guion bajo.")
    return code


def normalize_academic_year(value: str) -> str:
    year = value.strip()
    if not re.fullmatch(r"[1-9][0-9]{3}-[1-9][0-9]{3}", year) or int(year[:4]) + 1 != int(year[5:]):
        raise ValueError("Indica dos años consecutivos con formato AAAA-AAAA.")
    return year
