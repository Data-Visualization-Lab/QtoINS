from copy import deepcopy
import re
from typing import Any


def _extract_uuid_from_key(key: str) -> str | None:
    if not key:
        return None
    parts = key.split("+")
    if len(parts) >= 2:
        uuid_candidate = parts[-1].strip()
        if uuid_candidate:
            return uuid_candidate
    return None


def _extract_range_from_recommend(recommend_text: str) -> str | None:
    patterns = (
        r"from\s+(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)",
        r"(-?\d+(?:\.\d+)?)\s+to\s+(-?\d+(?:\.\d+)?)",
    )
    for pattern in patterns:
        match = re.search(pattern, recommend_text, flags=re.IGNORECASE)
        if match:
            return f"{match.group(1)} to {match.group(2)}"
    return None


def _normalize_text_solution(solution_value: Any) -> Any:
    if not isinstance(solution_value, dict):
        return solution_value

    key_map = {str(key).lower(): key for key in solution_value.keys()}
    summary_key = key_map.get("summary")
    recommend_key = key_map.get("recommend")
    if summary_key and recommend_key:
        recommend_value = solution_value.get(recommend_key)
        if isinstance(recommend_value, str):
            range_value = _extract_range_from_recommend(recommend_value)
            if range_value:
                return range_value
    return solution_value


def _append_uuid_solution(
    uuid_solution_map: dict[str, Any],
    uuid_value: str | None,
    solution_value: Any,
) -> None:
    if not uuid_value:
        return
    if solution_value is None:
        return

    copied_solution = deepcopy(solution_value)
    if uuid_value not in uuid_solution_map:
        uuid_solution_map[uuid_value] = copied_solution
        return

    existing = uuid_solution_map[uuid_value]
    if isinstance(existing, list):
        existing.append(copied_solution)
    else:
        uuid_solution_map[uuid_value] = [existing, copied_solution]


def build_initial_fuzzy_recommendations(
    text_recommend: dict[str, Any] | None,
    string_recommend: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Return the initial recommendation plan as {uuid: solution}.
    """
    text_recommend = text_recommend or {}
    string_recommend = string_recommend or {}
    uuid_solution_map: dict[str, Any] = {}

    for raw_key, detail in text_recommend.items():
        uuid_value = _extract_uuid_from_key(raw_key)
        if isinstance(detail, dict):
            solution_value = detail.get("solution")
        else:
            solution_value = detail
        solution_value = _normalize_text_solution(solution_value)
        if isinstance(detail, dict) and detail.get("single_select"):
            solution_value = {"options": solution_value, "single_select": True}
        _append_uuid_solution(uuid_solution_map, uuid_value, solution_value)

    for backend_key, columns in string_recommend.items():
        uuid_value = _extract_uuid_from_key(backend_key)
        if isinstance(columns, dict):
            for _, info in columns.items():
                if isinstance(info, dict):
                    solution_value = info.get("solution")
                else:
                    solution_value = info
                _append_uuid_solution(uuid_solution_map, uuid_value, solution_value)
        else:
            _append_uuid_solution(uuid_solution_map, uuid_value, columns)

    return uuid_solution_map
