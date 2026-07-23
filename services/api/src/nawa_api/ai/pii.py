"""The pseudonymizer (05-ai-infrastructure.md §5).

Applicant/member PII is replaced with stable placeholders before any payload
leaves for an external model; the mapping stays in Postgres (persistence lives
in db/pii + services/pii); responses are re-hydrated on the way back.

`pseudonymize` and `rehydrate` are PURE and side-effect-free — this module is
the canonical example of the slice's TDD discipline. Detection is
case-insensitive and tolerant of Arabic alef/yaa variants and Arabic-Indic
digits, but the stored mapping always records the EXACT matched substring, so
`rehydrate(pseudonymize(x)) == x` holds byte-for-byte.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

# --- token grammar ---------------------------------------------------------
# Plain uppercase-underscore tokens survive tokenizers and RTL text intact —
# no angle brackets or braces, which some models mangle.
_PREFIXES = ("PERSON", "EMAIL", "PHONE", "ORG", "ID")
_TOKEN_RE = re.compile(r"^(PERSON|EMAIL|PHONE|ORG|ID)_(\d+)$")

# Digit class covering ASCII and Arabic-Indic digits.
_D = r"[0-9٠-٩]"
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# National-ID-shaped: a standalone run of exactly 11 digits (Qatari QID length).
_ID_RE = re.compile(rf"(?<!{_D}){_D}{{11}}(?!{_D})")
# Phone: optional +, then 7+ digits with spaces/hyphens allowed between.
_PHONE_RE = re.compile(rf"\+?{_D}(?:[\s-]?{_D}){{6,}}")

# Arabic letter-variant folding for name matching.
_ALEF = "اأإآ"
_YAA = "يى"
_TASHKEEL = "ً-ٰٟ"


class KnownEntities(BaseModel):
    persons: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    phones: list[str] = Field(default_factory=list)
    orgs: list[str] = Field(default_factory=list)
    ids: list[str] = Field(default_factory=list)


class PiiMapping(BaseModel):
    # token -> original value, e.g. {"PERSON_1": "Amina El-Sayed"}
    tokens: dict[str, str] = Field(default_factory=dict)


def _known_pattern(value: str) -> re.Pattern[str] | None:
    """Case-insensitive regex for a known value, folding Arabic alef/yaa
    variants and tolerating optional tashkeel between characters."""
    stripped = value.strip()
    if not stripped:
        return None
    parts: list[str] = []
    for ch in stripped:
        if ch in _ALEF:
            parts.append(f"[{_ALEF}]")
        elif ch in _YAA:
            parts.append(f"[{_YAA}]")
        else:
            parts.append(re.escape(ch))
    # Allow optional tashkeel after each character so vocalised text still matches.
    body = f"[{_TASHKEEL}]*".join(parts)
    return re.compile(body, re.IGNORECASE)


def _next_index(mapping: dict[str, str], prefix: str) -> int:
    highest = 0
    for token in mapping:
        m = _TOKEN_RE.match(token)
        if m and m.group(1) == prefix:
            highest = max(highest, int(m.group(2)))
    return highest + 1


def pseudonymize(
    text: str, known: KnownEntities, prior: PiiMapping | None = None
) -> tuple[str, PiiMapping]:
    mapping: dict[str, str] = dict(prior.tokens) if prior else {}
    reverse: dict[str, str] = {original: token for token, original in mapping.items()}

    # Collect candidate (start, end, prefix, priority) spans. Lower priority wins
    # ties: known entities (0) beat pattern sweeps; among sweeps, id < phone so a
    # QID-shaped run is tagged ID before the phone rule can grab it.
    candidates: list[tuple[int, int, str, int]] = []

    def add_known(values: list[str], prefix: str) -> None:
        for value in sorted(set(values), key=len, reverse=True):  # longest-match-first
            pattern = _known_pattern(value)
            if pattern is None:
                continue
            for m in pattern.finditer(text):
                if m.end() > m.start():
                    candidates.append((m.start(), m.end(), prefix, 0))

    add_known(known.persons, "PERSON")
    add_known(known.orgs, "ORG")
    add_known(known.emails, "EMAIL")
    add_known(known.phones, "PHONE")
    add_known(known.ids, "ID")

    for m in _EMAIL_RE.finditer(text):
        candidates.append((m.start(), m.end(), "EMAIL", 1))
    for m in _ID_RE.finditer(text):
        candidates.append((m.start(), m.end(), "ID", 2))
    for m in _PHONE_RE.finditer(text):
        candidates.append((m.start(), m.end(), "PHONE", 3))

    # Greedy non-overlapping selection: earliest start, then longest, then
    # lowest priority.
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), c[3]))
    selected: list[tuple[int, int, str]] = []
    cursor = 0
    for start, end, prefix, _prio in candidates:
        if start >= cursor:
            selected.append((start, end, prefix))
            cursor = end

    # Rebuild the string, minting/reusing stable tokens per exact substring.
    out: list[str] = []
    last = 0
    for start, end, prefix in selected:
        out.append(text[last:start])
        substring = text[start:end]
        token = reverse.get(substring)
        if token is None:
            token = f"{prefix}_{_next_index(mapping, prefix)}"
            mapping[token] = substring
            reverse[substring] = token
        out.append(token)
        last = end
    out.append(text[last:])

    return "".join(out), PiiMapping(tokens=mapping)


def rehydrate(text: str, mapping: PiiMapping) -> str:
    # Longest-token-first so PERSON_10 is not clobbered by PERSON_1.
    for token in sorted(mapping.tokens, key=len, reverse=True):
        text = text.replace(token, mapping.tokens[token])
    return text
