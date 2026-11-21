"""DNI input shared by onboarding, sign-in and administrative tooling."""
import re

LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def normalize_dni(value: str) -> str:
    compact = re.sub(r"[ -]", "", value.strip()).upper()
    if not re.fullmatch(r"[0-9]{8}[A-Z]", compact) or LETTERS[int(compact[:8]) % 23] != compact[-1]:
        raise ValueError("DNI inválido. Escribe ocho dígitos y la letra de control.")
    return compact


def normalize_email(value: str) -> str:
    return value.strip().lower()
