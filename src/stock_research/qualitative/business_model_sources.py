from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PDD_SOURCE_COVERAGE = Path(
    "config/qualitative/pdd_business_model_source_coverage.v1.json"
)


def build_business_model_source_coverage(
    *,
    company: dict[str, Any],
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build source coverage for the Business Model Evidence Agent MVP.

    This is a registry-backed connector layer. It does not scrape live sites; it
    exposes source targets, local prototype links, collection methods, and
    coverage gaps in a stable shape downstream agents can consume.
    """

    company_id = str(company.get("company_id") or "").lower()
    registry = load_business_model_source_registry(company_id, registry_path=registry_path)
    groups = registry.get("source_groups") or []
    status_counts = Counter(str(group.get("status") or "unknown") for group in groups)
    priority_counts = Counter(str(group.get("priority") or "unknown") for group in groups)
    target_count = sum(len(group.get("source_targets") or []) for group in groups)
    local_targets = _local_target_status(groups)

    return {
        "status": registry.get("status") or "missing_registry",
        "company_id": company_id or registry.get("company_id") or "unknown",
        "registry_path": registry.get("registry_path"),
        "scope": registry.get("scope"),
        "source_groups": groups,
        "source_group_count": len(groups),
        "source_target_count": target_count,
        "status_counts": dict(sorted(status_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "local_target_status": local_targets,
        "coverage_policy": registry.get("coverage_policy", []),
        "top_connected_gaps": _top_connected_gaps(groups),
        "next_collection_steps": _next_collection_steps(groups),
    }


def load_business_model_source_registry(
    company_id: str,
    *,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    if registry_path is None:
        if company_id == "pdd":
            registry_path = DEFAULT_PDD_SOURCE_COVERAGE
        else:
            return _empty_registry(company_id)

    path = Path(registry_path)
    if not path.exists():
        return _empty_registry(company_id, missing_path=str(path))
    registry = json.loads(path.read_text(encoding="utf-8"))
    registry["registry_path"] = str(path)
    return registry


def _empty_registry(company_id: str, *, missing_path: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "company_id": company_id,
        "status": "missing_registry",
        "registry_path": missing_path,
        "scope": "Business-model source coverage is not configured for this company.",
        "source_groups": [],
        "coverage_policy": [],
    }


def _local_target_status(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for group in groups:
        for target in group.get("source_targets") or []:
            local_path = target.get("local_prototype_path")
            local_glob = target.get("local_path_glob")
            if not local_path and not local_glob:
                continue
            if local_path:
                path = Path(str(local_path))
                exists = path.exists()
                match_count = 1 if exists else 0
            else:
                matches = list(Path().glob(str(local_glob)))
                exists = bool(matches)
                match_count = len(matches)
            statuses.append(
                {
                    "group_id": group.get("group_id"),
                    "source_id": target.get("source_id"),
                    "path": local_path or local_glob,
                    "exists": exists,
                    "match_count": match_count,
                }
            )
    return statuses


def _top_connected_gaps(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "group_id": group.get("group_id"),
            "name": group.get("name"),
            "priority": group.get("priority"),
            "status": group.get("status"),
            "collector_status": group.get("collector_status"),
            "source_target_count": len(group.get("source_targets") or []),
            "evidence_role": group.get("evidence_role"),
        }
        for group in groups
    ]


def _next_collection_steps(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for group in groups:
        targets = group.get("source_targets") or []
        first = targets[0] if targets else {}
        locator = first.get("url") or first.get("locator") or first.get("local_path_glob")
        steps.append(
            {
                "group_id": group.get("group_id"),
                "name": group.get("name"),
                "priority": group.get("priority"),
                "status": group.get("status"),
                "collector_status": group.get("collector_status"),
                "first_locator": locator,
                "output_expectations": group.get("output_expectations", []),
            }
        )
    return steps
