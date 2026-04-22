from __future__ import annotations

from datetime import UTC, datetime
from html import unescape
import re
from typing import Iterable, TypeVar

T = TypeVar("T")

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def html_to_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = value.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    normalized = TAG_RE.sub(" ", normalized)
    normalized = unescape(normalized)
    return WHITESPACE_RE.sub(" ", normalized).strip()


def dedupe_preserve_order(values: Iterable[T]) -> list[T]:
    seen: set[T] = set()
    result: list[T] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def contains_any(haystack: str, needles: list[str]) -> bool:
    haystack_folded = haystack.casefold()
    return any(needle.casefold() in haystack_folded for needle in needles)
