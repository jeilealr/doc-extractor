"""Profiles match source evidence; they do not certify that extraction is correct."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import ExtractionResult
from .loader import Profile


@dataclass(frozen=True)
class Match:
    matched: bool
    checks: tuple[tuple[str, bool], ...]


def match_profile(profile: Profile, document: ExtractionResult) -> Match:
    if profile.file_format != document.file_format:
        return Match(False, (("file_format", False),))
    if profile.kind == "preset":
        return Match(True, (("generic-preset", True),))
    checks: list[tuple[str, bool]] = []
    search_text = "\n".join(page.text for page in document.pages).casefold()
    for term in profile.match.get("required_text", []):
        checks.append((f"required_text:{term}", term.casefold() in search_text))
    headers = profile.match.get("required_headers")
    if headers:
        expected = [h.casefold().strip() for h in headers]
        found = False
        for table in document.tables:
            if not table.cells:
                continue
            actual = [(c.text or "").casefold().strip() for c in table.cells[0]]
            if len(set(actual)) != len(actual):
                continue
            if all(h in actual for h in expected):
                found = True
                break
        checks.append(("required_headers", found))
    return Match(bool(checks) and all(passed for _, passed in checks), tuple(checks))
