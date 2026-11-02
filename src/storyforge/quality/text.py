"""Unicode checks and local text measurements. Input strings are never changed."""

import re
import unicodedata
from collections.abc import Iterator, Mapping

# Explicit embeddings, overrides, isolates, and deprecated directional controls.
_BIDI = frozenset(range(0x202A, 0x202F)) | frozenset(range(0x2066, 0x2070))
_BIDI_MARKS = frozenset((0x061C, 0x200E, 0x200F))
_SENTENCE_END = re.compile(r"[.!?…;\n\r\u05c3]+")


def forbidden_controls(text: str) -> bool:
    """Allow ordinary line whitespace and benign joiners, not hidden directives."""
    for char in text:
        code = ord(char)
        category = unicodedata.category(char)
        if code in _BIDI or code in _BIDI_MARKS:
            return True
        if category in ("Cc", "Cs") and char not in "\n\r\t":
            return True
        if category == "Cf" and char not in "\u200c\u200d":
            return True
    return False


def string_values(value: object) -> Iterator[str]:
    """Visit text at a trust boundary, including nested pronouns and metadata."""
    pending = [value]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if isinstance(current, str):
            yield current
        elif isinstance(current, (Mapping, tuple, list)):
            if id(current) in seen:
                continue
            seen.add(id(current))
            if isinstance(current, Mapping):
                for key, item in current.items():
                    pending.extend((key, item))
            else:
                pending.extend(current)


def sentences(text: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in _SENTENCE_END.split(text) if part.strip())


def _word_character(char: str) -> bool:
    return char == "_" or unicodedata.category(char)[0] in "LMN"


def name_spans(text: str, name: str) -> tuple[tuple[int, int], ...]:
    """Exact supplied code points, with Unicode word boundaries (no inflection)."""
    return tuple((match.start(), match.end()) for match in re.finditer(re.escape(name), text)
                 if (match.start() == 0 or not _word_character(text[match.start() - 1]))
                 and (match.end() == len(text) or not _word_character(text[match.end()])))


def without_name(text: str, name: str) -> str:
    pieces: list[str] = []
    start = 0
    for left, right in name_spans(text, name):
        pieces.extend((text[start:left], " "))
        start = right
    pieces.append(text[start:])
    return "".join(pieces)


def letter_counts(text: str, language: str) -> tuple[int, int]:
    letters = tuple(char for char in text if unicodedata.category(char).startswith("L"))
    script_name = "HEBREW" if language == "he" else "LATIN"
    matching = sum(script_name in unicodedata.name(char, "") for char in letters)
    return matching, len(letters)


def lexical_tokens(text: str) -> tuple[str, ...]:
    """Comparison copy only: canonicalize case/marks for narrow literal matching."""
    folded = unicodedata.normalize("NFKD", text).casefold()
    clean = "".join(char for char in folded if not unicodedata.category(char).startswith("M"))
    return tuple(re.findall(r"[^\W_]+", clean))


def contains_prohibited_directive(text: str, directives: tuple[str, ...]) -> bool:
    targets = {lexical_tokens(directive) for directive in directives}
    return any(lexical_tokens(sentence) in targets for sentence in sentences(text))
