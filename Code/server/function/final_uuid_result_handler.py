from __future__ import annotations

import re
from typing import Any

from sqlglot import exp, parse_one

from function.brace_toolkit import BraceSQLToolkit, DisallowedNodeError


_UUID_REGEX = re.compile(
    r"[0-9a-fA-F]{8}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}"
)

_REPLACE_SELECT = "replace_select"
_REPLACE_RANGE = "replace_range"
_REPLACE_EXACT = "replace_exact"
_REPLACE_FUZZY = "replace_fuzzy"


def _extract_uuid(raw_key: Any) -> str | None:
    if not isinstance(raw_key, str):
        return None
    key = raw_key.strip()
    if not key:
        return None

    if _UUID_REGEX.fullmatch(key):
        return key

    for part in reversed(key.split("+")):
        part = part.strip()
        if _UUID_REGEX.fullmatch(part):
            return part

    match = _UUID_REGEX.search(key)
    return match.group(0) if match else None


def _iter_uuid_value_pairs(final_uuid_result: Any) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []

    if isinstance(final_uuid_result, dict):
        items = [final_uuid_result]
    elif isinstance(final_uuid_result, list):
        items = final_uuid_result
    else:
        return pairs

    for item in items:
        if not isinstance(item, dict):
            continue
        for raw_uuid, value in item.items():
            uuid_value = _extract_uuid(str(raw_uuid))
            if not uuid_value:
                continue
            pairs.append((uuid_value, value))
    return pairs


def _build_uuid_type_map(
    textrecommend: dict[str, Any] | None,
    string_recommend_type: dict[str, str] | None,
) -> dict[str, str]:
    uuid_type_map: dict[str, str] = {}

    for raw_key, detail in (textrecommend or {}).items():
        uuid_value = _extract_uuid(raw_key)
        if not uuid_value:
            continue
        category = detail.get("category") if isinstance(detail, dict) else None
        if category == "multiple_column":
            uuid_type_map[uuid_value] = _REPLACE_SELECT
        elif category == "no_scientific_basis":
            uuid_type_map[uuid_value] = _REPLACE_RANGE

    for raw_uuid, match_type in (string_recommend_type or {}).items():
        uuid_value = _extract_uuid(raw_uuid)
        if not uuid_value:
            continue
        if match_type == "Exact Matching":
            uuid_type_map[uuid_value] = _REPLACE_EXACT
        elif match_type == "Fuzzy Matching":
            uuid_type_map[uuid_value] = _REPLACE_FUZZY

    return uuid_type_map


def _build_select_reference_map(textrecommend: dict[str, Any] | None) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for raw_key, detail in (textrecommend or {}).items():
        uuid_value = _extract_uuid(raw_key)
        if not uuid_value:
            continue
        if not isinstance(detail, dict):
            continue
        if detail.get("category") != "multiple_column":
            continue

        solution = detail.get("solution")
        if isinstance(solution, list):
            refs = [str(item).strip() for item in solution if str(item).strip()]
        elif solution is None:
            refs = []
        else:
            refs = [str(solution).strip()] if str(solution).strip() else []

        if refs:
            result[uuid_value] = _dedupe_non_empty(refs)
    return result


def _dedupe_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _strip_wrapping_quotes(value: str) -> str:
    trimmed = value.strip()
    if len(trimmed) >= 2 and trimmed[0] == trimmed[-1] and trimmed[0] in {"'", '"', "`"}:
        return trimmed[1:-1].strip()
    return trimmed


def _normalize_name_key(value: str) -> str:
    cleaned = _strip_wrapping_quotes(str(value))
    if "." in cleaned:
        cleaned = cleaned.split(".")[-1]
    return "".join(re.findall(r"[A-Za-z0-9]+", cleaned)).lower()


def _normalize_select_values(raw_value: Any, references: list[str] | None = None) -> list[str]:
    if isinstance(raw_value, list):
        source = [str(item).strip() for item in raw_value]
    elif raw_value is None:
        source = []
    else:
        source = [str(raw_value).strip()]

    normalized_source = _dedupe_non_empty(source)
    if not normalized_source:
        return []

    ref_map: dict[str, str] = {}
    for ref in references or []:
        key = _normalize_name_key(ref)
        if key:
            ref_map[key] = ref

    mapped: list[str] = []
    for item in normalized_source:
        mapped_value = ref_map.get(_normalize_name_key(item))
        if mapped_value:
            mapped.append(mapped_value)
            continue

        if " " in item and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ ]*", item):
            mapped.append(re.sub(r"\s+", "_", item.strip()))
            continue

        mapped.append(item)

    return _dedupe_non_empty(mapped)


def _normalize_range_bounds(raw_value: Any) -> tuple[str, str] | None:
    if isinstance(raw_value, (list, tuple)) and len(raw_value) >= 2:
        low = str(raw_value[0]).strip()
        high = str(raw_value[1]).strip()
        if low and high:
            return low, high

    if isinstance(raw_value, str):
        text = raw_value.strip()
        if not text:
            return None

        patterns = [
            r"from\s+(.+?)\s+to\s+(.+)$",
            r"(.+?)\s+to\s+(.+)$",
            r"(.+?)\s*(?:-|~|–|—)\s*(.+)$",
        ]
        for pattern in patterns:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if match:
                low = match.group(1).strip()
                high = match.group(2).strip()
                if low and high:
                    return low, high

    return None


def _to_exact_sql_literal(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return str(value)

    text = str(value).strip()
    if not text:
        return None

    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        if text[0] == "'":
            return text
        inner = text[1:-1].replace("'", "''")
        return f"'{inner}'"

    if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return text
    if text.upper() in {"NULL", "TRUE", "FALSE"}:
        return text.upper()

    escaped = text.replace("'", "''")
    return f"'{escaped}'"


def _normalize_exact_values(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        source = raw_value
    elif raw_value is None:
        source = []
    else:
        source = [raw_value]

    normalized: list[str] = []
    for item in source:
        lit = _to_exact_sql_literal(item)
        if lit:
            normalized.append(lit)
    return _dedupe_non_empty(normalized)


def _normalize_fuzzy_values(raw_value: Any) -> list[str]:
    if isinstance(raw_value, list):
        source = raw_value
    elif raw_value is None:
        source = []
    else:
        source = [raw_value]
    normalized = [_strip_wrapping_quotes(str(item)) for item in source]
    return _dedupe_non_empty(normalized)


def _safe_tree_sql(tree: Any, toolkit: BraceSQLToolkit) -> str:
    if tree is None or not hasattr(tree, "sql"):
        return ""
    try:
        return tree.sql(dialect=toolkit._BraceSQL)
    except Exception:
        return tree.sql()


def _parse_select_expression(raw_expr: str, toolkit: BraceSQLToolkit) -> exp.Expression:
    try:
        return parse_one(raw_expr, read=toolkit._BraceSQL)
    except Exception:
        quoted = raw_expr.replace('"', '""')
        return parse_one(f'"{quoted}"', read=toolkit._BraceSQL)


def _parse_range_side(raw_expr: str, toolkit: BraceSQLToolkit) -> exp.Expression:
    try:
        return parse_one(raw_expr, read=toolkit._BraceSQL)
    except Exception:
        escaped = raw_expr.replace("'", "''")
        return parse_one(f"'{escaped}'", read=toolkit._BraceSQL)


def _expr_has_uuid(expr_node: exp.Expression, target_uuid: str) -> bool:
    if expr_node.args.get("uuid") == target_uuid:
        return True
    for node in expr_node.walk():
        if getattr(node, "args", {}).get("uuid") == target_uuid:
            return True
    return False


def _projection_candidate_keys(projection: exp.Expression, toolkit: BraceSQLToolkit) -> set[str]:
    keys: set[str] = set()

    try:
        sql_text = projection.sql(dialect=toolkit._BraceSQL)
        key = _normalize_name_key(sql_text)
        if key:
            keys.add(key)
    except Exception:
        pass

    if isinstance(projection, exp.Column):
        name_key = _normalize_name_key(projection.name)
        if name_key:
            keys.add(name_key)

    alias_or_name = getattr(projection, "alias_or_name", None)
    if isinstance(alias_or_name, str) and alias_or_name.strip():
        alias_key = _normalize_name_key(alias_or_name)
        if alias_key:
            keys.add(alias_key)

    if isinstance(projection, exp.Alias):
        alias_name = projection.alias
        if isinstance(alias_name, str) and alias_name.strip():
            alias_key = _normalize_name_key(alias_name)
            if alias_key:
                keys.add(alias_key)
        if isinstance(projection.this, exp.Column):
            inner_key = _normalize_name_key(projection.this.name)
            if inner_key:
                keys.add(inner_key)

    return keys


def _replace_select_by_uuid_fallback(
    tree: Any,
    target_uuid: str,
    select_values: list[str],
    toolkit: BraceSQLToolkit,
) -> bool:
    select_node = tree.find(exp.Select) if isinstance(tree, exp.Expression) else None
    if not select_node or not select_values:
        return False

    replacement_exprs: list[exp.Expression] = []
    for raw_value in select_values:
        expr_node = _parse_select_expression(raw_value, toolkit)
        expr_node.set("uuid", target_uuid)
        replacement_exprs.append(expr_node)
    if not replacement_exprs:
        return False

    replaced = False
    inserted = False
    new_expressions: list[exp.Expression] = []

    for projection in select_node.expressions:
        if _expr_has_uuid(projection, target_uuid):
            replaced = True
            if not inserted:
                new_expressions.extend(expr.copy() for expr in replacement_exprs)
                inserted = True
            continue
        new_expressions.append(projection)

    if replaced:
        select_node.set("expressions", new_expressions)
    return replaced


def _replace_single_column_by_uuid(
    tree: Any,
    target_uuid: str,
    select_value: str,
    toolkit: BraceSQLToolkit,
) -> bool:
    replaced = False
    for node in list(tree.find_all(exp.Column)):
        if node.args.get("uuid") == target_uuid:
            replacement = _parse_select_expression(select_value, toolkit)
            replacement.set("uuid", target_uuid)
            node.replace(replacement)
            replaced = True
    return replaced


def _replace_select_by_solution_fallback(
    tree: Any,
    target_uuid: str,
    select_values: list[str],
    references: list[str],
    toolkit: BraceSQLToolkit,
) -> bool:
    select_node = tree.find(exp.Select) if isinstance(tree, exp.Expression) else None
    if not select_node or not select_values or not references:
        return False

    reference_keys = {_normalize_name_key(item) for item in references if _normalize_name_key(item)}
    if not reference_keys:
        return False

    replacement_exprs: list[exp.Expression] = []
    for raw_value in select_values:
        expr_node = _parse_select_expression(raw_value, toolkit)
        expr_node.set("uuid", target_uuid)
        replacement_exprs.append(expr_node)
    if not replacement_exprs:
        return False

    target_indices: list[int] = []
    for idx, projection in enumerate(select_node.expressions):
        if _expr_has_uuid(projection, target_uuid):
            target_indices.append(idx)
            continue
        projection_keys = _projection_candidate_keys(projection, toolkit)
        if projection_keys & reference_keys:
            target_indices.append(idx)

    if not target_indices:
        return False

    first_idx = target_indices[0]
    target_set = set(target_indices)
    new_expressions: list[exp.Expression] = []
    for idx, projection in enumerate(select_node.expressions):
        if idx == first_idx:
            new_expressions.extend(expr.copy() for expr in replacement_exprs)
        if idx in target_set:
            continue
        new_expressions.append(projection)

    select_node.set("expressions", new_expressions)
    return True


def _replace_range_by_uuid_fallback(
    tree: Any,
    target_uuid: str,
    low_str: str,
    high_str: str,
    toolkit: BraceSQLToolkit,
) -> bool:
    where_node = tree.find(exp.Where) if isinstance(tree, exp.Expression) else None
    if not where_node:
        return False

    replaced = False
    comparable_ops = (exp.EQ, exp.GT, exp.GTE, exp.LT, exp.LTE)

    def _build_low_high() -> tuple[exp.Expression, exp.Expression]:
        low_expr = _parse_range_side(low_str, toolkit)
        high_expr = _parse_range_side(high_str, toolkit)
        low_expr.set("uuid", target_uuid)
        high_expr.set("uuid", target_uuid)
        return low_expr, high_expr

    def _walk(node: exp.Expression) -> None:
        nonlocal replaced

        if isinstance(node, exp.Between):
            node_uid = node.args.get("uuid")
            low_uid = (
                node.args.get("low").args.get("uuid")
                if isinstance(node.args.get("low"), exp.Expression)
                else None
            )
            high_uid = (
                node.args.get("high").args.get("uuid")
                if isinstance(node.args.get("high"), exp.Expression)
                else None
            )
            if target_uuid in {node_uid, low_uid, high_uid}:
                low_expr, high_expr = _build_low_high()
                node.set("low", low_expr)
                node.set("high", high_expr)
                node.set("uuid", target_uuid)
                replaced = True
                return

        if isinstance(node, comparable_ops):
            right = node.expression
            right_uid = right.args.get("uuid") if isinstance(right, exp.Expression) else None
            if right_uid == target_uuid:
                low_expr, high_expr = _build_low_high()
                between_node = exp.Between(this=node.this.copy(), low=low_expr, high=high_expr)
                between_node.set("uuid", target_uuid)
                node.replace(between_node)
                replaced = True
                return

        for child in node.iter_expressions():
            _walk(child)

    _walk(where_node)
    return replaced


def apply_final_uuid_result(
    final_uuid_result: Any,
    tree: Any,
    textrecommend: dict[str, Any],
    string_recommend: dict[str, Any],
    string_recommend_type: dict[str, str] | None = None,
    column_names=None,
) -> exp.Expression | None:
    """
    Persist user-provided final uuid results into current backend context.
    This function mutates the tree in place and returns it.
    """
    print("final_uuid_result", final_uuid_result)
    toolkit = BraceSQLToolkit()
    print("tree before applying final uuid result", _safe_tree_sql(tree, toolkit))
    print("textrecommend before applying final uuid result", textrecommend)
    print("string_recommend before applying final uuid result", string_recommend)
    print("string_recommend_type", string_recommend_type or {})

    if tree is None:
        print("tree after applying final uuid result", tree)
        return

    uuid_type_map = _build_uuid_type_map(
        textrecommend=textrecommend,
        string_recommend_type=string_recommend_type,
    )
    select_reference_map = _build_select_reference_map(textrecommend)
    single_select_uuids = {
        _extract_uuid(key)
        for key, detail in (textrecommend or {}).items()
        if isinstance(detail, dict) and detail.get("single_select")
    }
    print("uuid_type_map", uuid_type_map)

    uuid_value_pairs = _iter_uuid_value_pairs(final_uuid_result)
    if not uuid_value_pairs:
        print("tree after applying final uuid result", _safe_tree_sql(tree, toolkit))
        return tree

    latest_uuid_values: dict[str, Any] = {}
    for uuid_value, raw_value in uuid_value_pairs:
        latest_uuid_values[uuid_value] = raw_value

    for uuid_value, raw_value in latest_uuid_values.items():
        replace_kind = uuid_type_map.get(uuid_value)
        if not replace_kind:
            print(f"skip uuid {uuid_value}: no mapped replacement type")
            continue

        print(f"applying uuid {uuid_value} with type {replace_kind}, raw value={raw_value}")
        before_sql = _safe_tree_sql(tree, toolkit)

        if replace_kind == _REPLACE_SELECT:
            select_refs = select_reference_map.get(uuid_value, [])
            select_values = _normalize_select_values(raw_value, references=select_refs)
            if column_names is not None:
                select_values = [
                    exp.column(value).sql(dialect=toolkit._BraceSQL) if value in column_names else value
                    for value in select_values
                ]
            if uuid_value in single_select_uuids:
                if len(select_values) != 1:
                    raise DisallowedNodeError("Please select exactly one column.")
                selected_column = _parse_select_expression(select_values[0], toolkit)
                if not isinstance(selected_column, exp.Column):
                    raise DisallowedNodeError("Please select a column from the table.")
                if column_names is not None and selected_column.name not in column_names:
                    raise DisallowedNodeError("Please select a column from the table.")
            if not select_values:
                print(f"skip uuid {uuid_value}: empty select values")
                continue
            toolkit.substitute_select_placeholders_on_tree(tree, {uuid_value: select_values})
            after_sql = _safe_tree_sql(tree, toolkit)
            changed = after_sql != before_sql
            if uuid_value in single_select_uuids:
                _replace_single_column_by_uuid(
                    tree=tree,
                    target_uuid=uuid_value,
                    select_value=select_values[0],
                    toolkit=toolkit,
                )
                continue
            if not changed:
                changed = _replace_select_by_uuid_fallback(
                    tree=tree,
                    target_uuid=uuid_value,
                    select_values=select_values,
                    toolkit=toolkit,
                )
            if not changed:
                _replace_select_by_solution_fallback(
                    tree=tree,
                    target_uuid=uuid_value,
                    select_values=select_values,
                    references=select_refs,
                    toolkit=toolkit,
                )

        elif replace_kind == _REPLACE_RANGE:
            bounds = _normalize_range_bounds(raw_value)
            if not bounds:
                print(f"skip uuid {uuid_value}: invalid range value")
                continue
            low, high = bounds
            toolkit.substitute_where_range_placeholders_on_tree(
                tree,
                {uuid_value: f"{low} - {high}"},
            )
            after_sql = _safe_tree_sql(tree, toolkit)
            if after_sql == before_sql:
                _replace_range_by_uuid_fallback(
                    tree=tree,
                    target_uuid=uuid_value,
                    low_str=low,
                    high_str=high,
                    toolkit=toolkit,
                )

        elif replace_kind == _REPLACE_EXACT:
            exact_values = _normalize_exact_values(raw_value)
            if not exact_values:
                print(f"skip uuid {uuid_value}: empty exact values")
                continue
            toolkit.substitute_where_equal_to_in_on_tree(tree, {uuid_value: exact_values})

        elif replace_kind == _REPLACE_FUZZY:
            fuzzy_values = _normalize_fuzzy_values(raw_value)
            if not fuzzy_values:
                print(f"skip uuid {uuid_value}: empty fuzzy values")
                continue
            toolkit.substitute_where_like_to_or_on_tree(tree, {uuid_value: fuzzy_values})

    print("tree after applying final uuid result", _safe_tree_sql(tree, toolkit))
    print("tree sql after applying final uuid result", _safe_tree_sql(tree, toolkit))
    return tree
