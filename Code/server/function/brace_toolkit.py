from __future__ import annotations

import uuid
from typing import Any, Dict, List, Tuple, Union
from itertools import product

import sqlglot
from sqlglot import exp, parse_one
from sqlglot.dialects.dialect import Dialect
from sqlglot.errors import ParseError
from sqlglot.generator import Generator as BaseGenerator
from sqlglot.tokens import TokenType


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #

class DisallowedNodeError(Exception):
    pass


class Brace(exp.Expression):
    arg_types = {"this": True, "uuid": False}

    @property
    def id(self) -> str:
        return self.args.get("uuid", "")


class CustomDialect(Dialect):
    

    class Tokenizer(sqlglot.tokens.Tokenizer):
        
        ...

    class Parser(sqlglot.parser.Parser):
        def _parse_primary(self):
            
            if self._match(TokenType.L_BRACE):
                inner = self._parse_expression()
                if not self._match(TokenType.R_BRACE):
                    self.raise_error("Expecting '}'")
                
                node = Brace(this=inner, uuid=str(uuid.uuid4()))
                return node

            return super()._parse_primary()

    class Generator(BaseGenerator):
        TRANSFORMS = {
            **BaseGenerator.TRANSFORMS,
            Brace: lambda self, e: "{" + self.sql(e, "this") + "}",
        }


ALLOWED_NODE_TYPES = {
    exp.Select,
    exp.From,
    exp.Where,
    exp.Group,
    exp.Order,
    exp.Ordered,
    exp.Column,
    exp.Like,
    exp.ILike,
    exp.Identifier,
    exp.Table,
    exp.Literal,
    exp.EQ,
    exp.In,
    exp.Between,
    exp.Condition,
    exp.Max,
    exp.Min,
    exp.Count,
    exp.Sum,
    exp.Avg,
    exp.Or,
    exp.Add,
    exp.Sub,
    exp.Mul,
    exp.Div,
    exp.Paren,
    exp.Neg,

    
    exp.Alias,          # COUNT(*) AS AthleteCount
    exp.Star,           # COUNT(*)
    exp.And,            # Year > 2016 AND Age > {older}
    exp.Limit,          # LIMIT 3
    exp.GT,             # >
    exp.GTE,            # >=
    exp.LT,             # <
    exp.LTE,            # <=

    
    Brace,
}


def _ensure_uuid(node: exp.Expression) -> str:
    uid = node.args.get("uuid")
    if uid:
        return uid
    uid = str(uuid.uuid4())
    node.set("uuid", uid)
    return uid


def _seed_initial_uuids(tree: exp.Expression) -> None:
    
    for node in tree.find_all(Brace):
        _ensure_uuid(node)

    for node in tree.find_all(exp.In):
        group_uid = _ensure_uuid(node)
        for item in node.expressions or []:
            if isinstance(item, exp.Expression):
                item.set("uuid", group_uid)

    for node in tree.find_all(exp.Literal):
        parent = node.parent
        if isinstance(parent, exp.In) and node in (parent.expressions or []):
            
            if not node.args.get("uuid"):
                node.set("uuid", _ensure_uuid(parent))
            continue
        _ensure_uuid(node)


def _check_node(node: exp.Expression):
    
    if type(node) not in ALLOWED_NODE_TYPES:
        raise DisallowedNodeError(f"Disallowed node type detected: {type(node).__name__}")

    for arg in node.args.values():
        if isinstance(arg, list):
            for c in arg:
                if isinstance(c, exp.Expression):
                    _check_node(c)
        elif isinstance(arg, exp.Expression):
            _check_node(arg)


def _check_where_predicates(tree: exp.Expression, column_names=None):
    known_columns = None if column_names is None else {str(name).casefold(): str(name) for name in column_names}
    comparison_types = (exp.EQ, exp.GT, exp.GTE, exp.LT, exp.LTE, exp.Like, exp.ILike)
    range_types = (exp.GT, exp.GTE, exp.LT, exp.LTE)

    def _check_column(node):
        if not isinstance(node, exp.Column):
            raise DisallowedNodeError("The left operand of a WHERE predicate must be a column")
        if known_columns is not None:
            column_name = known_columns.get(node.name.casefold())
            if column_name is None:
                raise DisallowedNodeError(f"Unknown column in WHERE: {node.name}")
            node.this.set("this", column_name)

    def _is_value(node, allow_placeholder=False):
        if isinstance(node, exp.Paren):
            return _is_value(node.this, allow_placeholder)
        if isinstance(node, exp.Literal):
            return True
        if isinstance(node, exp.Neg):
            return isinstance(node.this, exp.Literal) and not node.this.is_string
        return allow_placeholder and isinstance(node, Brace)

    def _check_value(node, allow_placeholder=False):
        if not _is_value(node, allow_placeholder):
            raise DisallowedNodeError("The right operand of a WHERE predicate must be a literal value")

    def _walk(node):
        if isinstance(node, exp.Paren):
            _walk(node.this)
        elif isinstance(node, (exp.And, exp.Or)):
            _walk(node.this)
            _walk(node.expression)
        elif isinstance(node, comparison_types):
            _check_column(node.this)
            _check_value(node.expression, isinstance(node, range_types))
        elif isinstance(node, exp.In):
            _check_column(node.this)
            if not node.expressions:
                raise DisallowedNodeError("IN must contain at least one literal value")
            for value in node.expressions:
                _check_value(value)
        elif isinstance(node, exp.Between):
            _check_column(node.this)
            _check_value(node.args.get("low"))
            _check_value(node.args.get("high"))
        else:
            raise DisallowedNodeError("WHERE conditions must compare a column with a value")

    for where in tree.find_all(exp.Where):
        _walk(where.this)


def _check_placeholder_positions(tree: exp.Expression):
    
    infos: List[Dict[str, Any]] = []
    allowed_cmp_types = (exp.GT, exp.GTE, exp.LT, exp.LTE)
    column_placeholders = {}

    for node in tree.find_all(Brace):
        _ensure_uuid(node)
        
        select_ancestor = node.find_ancestor(exp.Select)
        inner_sql = node.this.sql(dialect=CustomDialect) if node.this is not None else None
        if not select_ancestor:
            raise DisallowedNodeError("Placeholders must appear inside a SELECT statement")

        
        limit_ancestor = node.find_ancestor(exp.Limit)
        if limit_ancestor is not None:
            raise DisallowedNodeError("Placeholders in LIMIT are not supported; use a numeric limit")

        
        
        where_ancestor = node.find_ancestor(exp.Where)
        if where_ancestor is not None:
            
            cmp = node.find_ancestor(*allowed_cmp_types, exp.EQ)
            if cmp is None:
                raise DisallowedNodeError(
                    "A placeholder in WHERE must appear inside a comparison expression, e.g. B > {C}"
                )

            if not cmp.find_ancestor(exp.Where):
                raise DisallowedNodeError(
                    "A placeholder in WHERE must be part of a WHERE condition expression"
                )

            
            right = cmp.args.get("expression")
            if right is not node:
                raise DisallowedNodeError(
                    "Placeholders in WHERE must appear on the right side of the comparison, e.g. B > {C}"
                )

            if type(cmp) not in allowed_cmp_types:
                raise DisallowedNodeError(
                    "Comparisons containing placeholders may only use >, >=, <, <= — '=' is not allowed"
                )

            
            left = cmp.this
            
            left_sql = left.sql(dialect=CustomDialect) if isinstance(left, exp.Expression) else None

            
            left_col_name = None
            if isinstance(left, exp.Column):
                
                left_col_name = left.name
            elif isinstance(left, exp.Identifier):
                left_col_name = left.this

            parent = node.parent
            infos.append(
                {
                    "uuid": node.id,
                    "allowed_context": "WhereComparison",
                    "direct_parent": type(parent).__name__ if parent is not None else None,
                    "inner_sql": inner_sql,                       
                    "placeholder_sql": node.sql(dialect=CustomDialect),  # "{year_min}"
                    "where_left_sql": left_sql,                   
                    "where_left_col": left_col_name,              
                    "single_select": False,
                }
            )
            continue


        
        group_ancestor = node.find_ancestor(exp.Group)
        if group_ancestor is not None:
            
            cur = node
            while cur.parent is not None and cur.parent is not group_ancestor:
                cur = cur.parent

            group_expressions = group_ancestor.args.get("expressions") or []
            if cur not in group_expressions:
                raise DisallowedNodeError(
                    "Placeholders in GROUP BY must be used directly as grouping key expressions, "
                    "e.g. GROUP BY {group_expr}"
                )

            parent = node.parent
            infos.append(
                {
                    "uuid": node.id,
                    "inner_sql": inner_sql,    
                    "allowed_context": "GroupBy",
                    "direct_parent": type(parent).__name__ if parent is not None else None,
                    "single_select": True,
                }
            )
            column_placeholders.setdefault((id(select_ancestor), inner_sql), []).append((node, infos[-1]))
            continue

        
        cur = node
        while cur.parent is not None and cur.parent is not select_ancestor:
            cur = cur.parent

        projections = select_ancestor.args.get("expressions") or []
        if cur not in projections:
            raise DisallowedNodeError(
                "Placeholders are only allowed in SELECT projection list, GROUP BY keys, "
                "or on the right-hand side of WHERE comparisons like B > {C}; "
                "they are not allowed in other locations (such as ORDER BY)."
            )

        parent = node.parent
        infos.append(
            {
                "uuid": node.id,
                "inner_sql": inner_sql,    
                "allowed_context": "Select",
                "direct_parent": type(parent).__name__ if parent is not None else None,
                "single_select": node.find_ancestor(exp.AggFunc) is not None,
            }
        )
        column_placeholders.setdefault((id(select_ancestor), inner_sql), []).append((node, infos[-1]))

    for occurrences in column_placeholders.values():
        shared_uuid = occurrences[0][0].id
        single_select = any(info["single_select"] for _, info in occurrences)
        for node, info in occurrences:
            node.set("uuid", shared_uuid)
            info["uuid"] = shared_uuid
            info["single_select"] = single_select

    return infos


def validate_tree_strict(tree: exp.Expression, column_names=None) -> Tuple[exp.Expression, List[Dict[str, Any]]]:
    _check_node(tree)
    _check_where_predicates(tree, column_names)
    placeholder_infos = _check_placeholder_positions(tree)
    _seed_initial_uuids(tree)
    return tree, placeholder_infos


def validate_sql_strict(sql: str, column_names=None) -> Tuple[exp.Expression, List[Dict[str, Any]]]:
    tree = parse_one(sql, read=CustomDialect)
    return validate_tree_strict(tree, column_names)


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #

class BraceSQLToolkit:
    
    
    Brace = Brace
    _BraceSQL = CustomDialect

    
    _ALLOWED_PRED = (exp.Binary, exp.In)

    
    def has_placeholder(self, sql: str) -> bool:
        try:
            tree = self.parse(sql)
            return any(isinstance(n, self.Brace) for n in tree.walk())
        except ParseError:
            return False

    
    def parse(self, sql: str) -> exp.Expression:
        
        tree, _ = validate_sql_strict(sql)
        return tree

    def transpile(self, sql: str) -> str:
        return self.parse(sql).sql(dialect=self._BraceSQL)

    def brace_locations(self, sql: str) -> list[tuple]:
        _, infos = validate_sql_strict(sql)
        return [(x["allowed_context"], x["uuid"]) for x in infos]

    
    def invalid_predicates(self, sql: str) -> List[Tuple[str, str]]:
        
        errors: list[tuple[str, str]] = []
        try:
            validate_sql_strict(sql)
        except ParseError as e:
            errors.append(("SYNTAX", str(e).split("\n", 1)[0]))
        except DisallowedNodeError as e:
            errors.append(("VALIDATE", str(e)))
        return errors

    def check(self, sql: str, explain: bool = False) -> Tuple[bool, str | None]:
        errs = self.invalid_predicates(sql)
        if errs:
            reason = "; ".join(f"[{tag}] {msg}" for tag, msg in errs) if explain else None
            return False, reason
        return True, None

    

    def substitute_select_placeholders_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, str | list[str]],
    ) -> str:
        
        infos = _check_placeholder_positions(tree)
        column_infos = [info for info in infos if info["allowed_context"] in ("Select", "GroupBy")]
        column_uuids = {info["uuid"] for info in column_infos}
        for info in column_infos:
            replacement = replacements.get(info["uuid"])
            if info["single_select"] and isinstance(replacement, list) and len(replacement) != 1:
                raise DisallowedNodeError("An aggregate argument or GROUP BY placeholder requires exactly one column")

        def _expr_with_uid(x, uid: str):
            node = x.copy() if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)
            node.set("uuid", uid)
            return node

        def _replace_expression(expression):
            choices = {}
            for node in expression.find_all(self.Brace):
                if node.id not in column_uuids or node.id in choices:
                    continue
                replacement = replacements.get(node.id)
                if replacement is None:
                    continue
                values = replacement if isinstance(replacement, list) else [replacement]
                choices[node.id] = [_expr_with_uid(value, node.id) for value in values]
            if not choices:
                return [expression]

            expressions = []
            keys, vals_list = zip(*choices.items())
            for combo in product(*vals_list):
                clone = expression.copy()
                for uid, val in zip(keys, combo):
                    if isinstance(clone, self.Brace) and clone.id == uid:
                        clone = val.copy()
                        continue
                    for node in list(clone.find_all(self.Brace)):
                        if node.id == uid:
                            node.replace(val.copy())
                expressions.append(clone)
            return expressions

        for select in tree.find_all(exp.Select):
            new_projs = []
            for projection in select.expressions:
                new_projs.extend(_replace_expression(projection))
            select.set("expressions", new_projs)

            group = select.args.get("group")
            if group is not None:
                new_keys = []
                for key in group.expressions:
                    new_keys.extend(_replace_expression(key))
                group.set("expressions", new_keys)
        return tree.sql(dialect=self._BraceSQL)

    def substitute_where_range_placeholders_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, str | list[str]],
    ) -> str:
        
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)

        def _walk(node: exp.Expression):
            
            if isinstance(node, exp.Binary) and isinstance(node.expression, self.Brace):
                brace_node: Brace = node.expression
                uid = brace_node.id
                repl = replacements.get(uid)

                
                if isinstance(repl, str) and "-" in repl:
                    low_str, high_str = [p.strip() for p in repl.split("-", 1)]
                    low = parse_one(low_str, read=self._BraceSQL)
                    high = parse_one(high_str, read=self._BraceSQL)
                    low.set("uuid", uid)
                    high.set("uuid", uid)

                    between = exp.Between(
                        this=node.this.copy(),   
                        low=low,
                        high=high,
                    )
                    between.set("uuid", uid)
                    node.replace(between)
                    return  

            
            for child in node.iter_expressions():
                _walk(child)

        _walk(where)
        return tree.sql(dialect=self._BraceSQL)

    def parse_sql_to_json(self, sql_or_tree: Union[str, exp.Expression]) -> Dict[str, Any]:
        
        # ---------- ① AST ----------
        tree = sql_or_tree if isinstance(sql_or_tree, exp.Expression) else self.parse(sql_or_tree)
        
        _seed_initial_uuids(tree)
        where: exp.Where | None = tree.find(exp.Where)
        if not where:
            return {"type": False}

        
        def _collect_preds(node: exp.Expression):
            if isinstance(node, self._ALLOWED_PRED) and not isinstance(node, (exp.And, exp.Or)):
                yield node
            else:
                for child in node.iter_expressions():
                    yield from _collect_preds(child)

        
        def _lit(node: exp.Expression) -> str:
            return node.sql(dialect=self._BraceSQL).strip("'\"{}")

        result: Dict[str, Any] = {"type": True}

        
        def _flatten_or(e):
            if isinstance(e, exp.Or):
                yield from _flatten_or(e.this)
                yield from _flatten_or(e.expression)
            else:
                yield e

        for idx, disjunction in enumerate(_flatten_or(where.this)):
            col_names, match_types, match_values = [], [], []

            for pred in _collect_preds(disjunction):
                col_names.append(pred.this.sql(dialect=self._BraceSQL))
                is_like = isinstance(pred, (exp.Like, exp.ILike))
                match_types.append("Fuzzy Matching" if is_like else "Exact Matching")

                
                if isinstance(pred, exp.In):
                    group_uid = _ensure_uuid(pred)
                    vals = []
                    for lit in pred.expressions:
                        if isinstance(lit, exp.Expression):
                            lit.set("uuid", group_uid)
                        vals.append(_lit(lit))
                    vals.append(group_uid)  
                    match_values.append([vals])

                
                else:
                    right = getattr(pred, "expression", None)
                    if right is None:
                        # e.g. BETWEEN, which has .low / .high – skip or handle separately
                        continue

                    uid = _ensure_uuid(right)
                    match_values.append([[_lit(right), uid]])

            result[f"condition_{idx}"] = [[col_names], [match_types], match_values]

        return result

    def substitute_where_equal_to_in_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, list[str | exp.Expression]],
    ) -> str:
        
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)
        _seed_initial_uuids(tree)

        def _expr(x):
            return x if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)

        def _walk(node: exp.Expression):
            
            if isinstance(node, exp.In) and node.expressions:
                uid = node.args.get("uuid") or node.expressions[0].args.get("uuid")
                if uid and uid in replacements:
                    raw_vals = replacements[uid]
                    raw_vals = raw_vals if isinstance(raw_vals, list) else [raw_vals]

                    new_vals = []
                    for v in raw_vals:
                        val_ast = _expr(v)
                        val_ast.set("uuid", uid)
                        new_vals.append(val_ast)

                    node.set("uuid", uid)
                    node.set("expressions", new_vals)

            # -------- EQ → IN ----------
            if isinstance(node, exp.EQ):
                right = node.expression
                if isinstance(right, (exp.Literal, self.Brace)):
                    uid = right.args.get("uuid")
                    if uid and uid in replacements and isinstance(replacements[uid], list):
                        in_vals = []
                        for v in replacements[uid]:
                            val_ast = _expr(v)
                            val_ast.set("uuid", uid)
                            in_vals.append(val_ast)
                        in_pred = exp.In(this=node.this.copy(), expressions=in_vals)
                        in_pred.set("uuid", uid)
                        node.replace(in_pred)
                        return

            
            for child in node.iter_expressions():
                _walk(child)

        _walk(where)
        return tree.sql(dialect=self._BraceSQL)

    def substitute_where_like_to_or_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, list[str | exp.Expression]],
        wrap_wildcards: bool = True,
    ) -> str:
        
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)
        _seed_initial_uuids(tree)

        def _expr(x):
            return x if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)

        def _make_like(column_ast: exp.Expression, pattern_ast: exp.Expression, like_cls):
            return like_cls(this=column_ast.copy(), expression=pattern_ast)

        def _walk(node: exp.Expression):
            
            if isinstance(node, (exp.Like, exp.ILike)):
                right = node.expression
                if isinstance(right, (exp.Literal, self.Brace)):
                    uid = right.args.get("uuid")
                    if uid and uid in replacements and isinstance(replacements[uid], list):
                        or_chain = None
                        like_cls = exp.ILike if isinstance(node, exp.ILike) else exp.Like

                        for raw in replacements[uid]:
                            if isinstance(raw, str) and wrap_wildcards:
                                raw = f"'%{raw.strip('%')}%'"
                            pat_ast = _expr(raw)
                            pat_ast.set("uuid", uid)
                            like_node = _make_like(node.this, pat_ast, like_cls)
                            or_chain = like_node if or_chain is None else exp.Or(
                                this=or_chain, expression=like_node
                            )

                        node.replace(or_chain)
                        return

            for child in node.iter_expressions():
                _walk(child)

        _walk(where)
        return tree.sql(dialect=self._BraceSQL)
