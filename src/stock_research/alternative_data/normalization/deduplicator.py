from __future__ import annotations

from typing import Any


def dedupe_by_key(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for item in items:
        value = item.get(key)
        if value in seen:
            continue
        seen.add(value)
        deduped.append(item)
    return deduped
