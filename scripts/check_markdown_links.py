#!/usr/bin/env python3
"""Validate local Markdown / HTML asset links in this repository.

Checks relative file, directory, and image targets. Same-file heading anchors
are validated with a GitHub-like slug. External http(s)/mailto/data URLs are
skipped. Exit 0 on success, 1 on any broken local reference.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIR_PARTS = {
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".git",
    ".pytest_cache",
    "test-results",
    "playwright-report",
    "__pycache__",
}

LINK_RE = re.compile(
    r"\[(?:[^\]]*)\]\(([^)]+)\)|"
    r"<(?:img|source|a)[^>]+(?:src|srcset|href)=\"([^\"]+)\"",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
HTML_ID_RE = re.compile(r'<a\s+id="([^"]+)"', re.IGNORECASE)


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIR_PARTS for part in path.parts)


def github_slug(heading: str) -> str:
    text = heading.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    return text


def collect_anchors(text: str) -> set[str]:
    anchors = {github_slug(m.group(2)) for m in HEADING_RE.finditer(text)}
    anchors.update(HTML_ID_RE.findall(text))
    return anchors


def iter_markdown_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.md"):
        if should_skip(path.relative_to(ROOT)):
            continue
        files.append(path)
    return sorted(files)


def extract_targets(raw: str) -> list[str]:
    targets: list[str] = []
    for match in LINK_RE.finditer(raw):
        value = match.group(1) or match.group(2) or ""
        # srcset may list multiple candidates
        for piece in re.split(r"\s*,\s*", value):
            url = piece.strip().split()[0] if piece.strip() else ""
            if url:
                targets.append(url)
    return targets


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    anchors = collect_anchors(text)
    rel = path.relative_to(ROOT).as_posix()
    errors: list[str] = []

    for url in extract_targets(text):
        if url.startswith(("http://", "https://", "mailto:", "data:")):
            continue

        file_part, _, fragment = url.partition("#")
        if not file_part:
            if fragment and fragment not in anchors:
                errors.append(f"{rel}: missing same-file anchor #{fragment}")
            continue

        target = (path.parent / file_part).resolve()
        try:
            target.relative_to(ROOT.resolve())
        except ValueError:
            errors.append(f"{rel}: escapes repo root -> {url}")
            continue

        if not target.exists():
            errors.append(f"{rel}: missing target -> {url}")
            continue

        if fragment and target.is_file() and target.suffix.lower() == ".md":
            target_anchors = collect_anchors(target.read_text(encoding="utf-8"))
            if fragment not in target_anchors:
                errors.append(f"{rel}: missing anchor in {file_part} -> #{fragment}")

    return errors


def main() -> int:
    errors: list[str] = []
    files = iter_markdown_files()
    for path in files:
        errors.extend(check_file(path))

    if errors:
        print(f"Broken local markdown links ({len(errors)}):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"OK: checked {len(files)} markdown file(s); no broken local links.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
