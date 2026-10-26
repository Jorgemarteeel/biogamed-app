"""Comparison rules shared by Pasapalabra validation and scoring."""
import unicodedata


def normalize_answer(value: str) -> str:
    # Preserve ñ: it is a different letter in Spanish, not an accented n.
    value = unicodedata.normalize("NFC", value).casefold()
    value = value.translate(str.maketrans("áéíóúü", "aeiouu"))
    return " ".join(value.split())


def is_accepted_answer(value: str, exact_word: str, alternatives: list[str] | None) -> bool:
    normalized = normalize_answer(value)
    return bool(normalized) and any(
        normalized == normalize_answer(candidate)
        for candidate in [exact_word, *(alternatives or [])]
    )
