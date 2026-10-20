"""Alias normalization and synonym resolution."""

from __future__ import annotations

import re

_SEPARATORS = re.compile(r"[^a-z0-9+#]+")


def normalize_alias(value: str) -> str:
    """Fold a skill label into a match token.

    Case, punctuation, and whitespace are folded. ``+`` and ``#`` are kept so
    ``C++`` and ``C#`` stay distinct. This does not apply the alias dictionary;
    callers resolve tokens against stored aliases.
    """

    text = value.strip().lower().replace("&", " and ")
    text = _SEPARATORS.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_alias_index(
    skills: list[tuple[int, str, tuple[str, ...] | list[str]]],
) -> dict[str, int]:
    """Map normalized canonical names and aliases to skill ids.

    Raises ValueError if two skills claim the same token.
    """

    index: dict[str, int] = {}
    owners: dict[str, str] = {}
    for skill_id, canonical, aliases in skills:
        tokens = [canonical, *list(aliases)]
        for token in tokens:
            folded = normalize_alias(token)
            if not folded:
                continue
            previous = index.get(folded)
            if previous is not None and previous != skill_id:
                raise ValueError(
                    f"Alias collision on {folded!r}: {owners[folded]!r} and {canonical!r}"
                )
            index[folded] = skill_id
            owners[folded] = canonical
    return index


def resolve_skill_id(label: str, alias_index: dict[str, int]) -> int | None:
    if not label or not label.strip():
        return None
    return alias_index.get(normalize_alias(label))
