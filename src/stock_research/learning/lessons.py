from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_LESSON_REGISTRY = Path("config/learning/user_lessons.v1.json")


def load_lesson_registry(path: str | Path = DEFAULT_LESSON_REGISTRY) -> dict[str, Any]:
    registry_path = Path(path)
    if not registry_path.exists():
        return {
            "schema_version": 1,
            "activation_policy": {
                "behavior_rule": "No lesson registry found. Agents run without learning-material overrides."
            },
            "source_materials": [],
            "agent_lessons": {},
        }
    return json.loads(registry_path.read_text(encoding="utf-8"))


def lesson_status_counts(registry: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for lessons in registry.get("agent_lessons", {}).values():
        for lesson in lessons:
            counts[str(lesson.get("status", "unknown"))] += 1
    return dict(sorted(counts.items()))


def lessons_for_agent(
    agent_id: str,
    *,
    status: str | None = None,
    registry: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    registry = registry or load_lesson_registry()
    lessons = list(registry.get("agent_lessons", {}).get(agent_id, []))
    if status is None:
        return lessons
    return [lesson for lesson in lessons if lesson.get("status") == status]


def lesson_context_for_agent(agent_id: str, *, max_lessons: int = 5) -> dict[str, Any]:
    registry = load_lesson_registry()
    all_lessons = lessons_for_agent(agent_id, registry=registry)
    approved = [lesson for lesson in all_lessons if lesson.get("status") == "approved"]
    candidates = [lesson for lesson in all_lessons if lesson.get("status") == "candidate"]
    return {
        "agent_id": agent_id,
        "registry_path": str(DEFAULT_LESSON_REGISTRY),
        "activation_rule": registry.get("activation_policy", {}).get("behavior_rule"),
        "total_lessons": len(all_lessons),
        "approved_lessons": approved[:max_lessons],
        "candidate_lessons": candidates[:max_lessons],
        "status_counts": lesson_status_counts(registry),
    }


def build_lesson_report(registry_path: str | Path = DEFAULT_LESSON_REGISTRY) -> str:
    registry = load_lesson_registry(registry_path)
    counts = lesson_status_counts(registry)
    source_titles = [
        f"{source.get('title')} (`{source.get('source_id')}`)"
        for source in registry.get("source_materials", [])
    ]
    lines = [
        "# Learning Lesson Registry",
        "",
        f"- Registry: `{registry_path}`",
        f"- Schema version: {registry.get('schema_version')}",
        f"- Activation rule: {registry.get('activation_policy', {}).get('behavior_rule')}",
        "- Status counts: "
        + (", ".join(f"{status}: {count}" for status, count in counts.items()) or "none"),
        "",
        "## Source Materials",
        "",
        "\n".join(f"- {title}" for title in source_titles) or "- None",
        "",
        "## Lessons By Agent",
        "",
    ]
    for agent_id, lessons in sorted(registry.get("agent_lessons", {}).items()):
        lines.append(f"### {agent_id}")
        lines.append("")
        for lesson in lessons:
            lines.append(
                f"- `{lesson.get('lesson_id')}` [{lesson.get('status')}]: {lesson.get('lesson')}"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"
