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
#                            占位符表达式 & 校验                               #
# --------------------------------------------------------------------------- #

class DisallowedNodeError(Exception):
    """在严格校验中发现不允许的 AST 节点类型或非法占位符位置时抛出。"""
    pass


class Brace(exp.Expression):
    """自定义占位符表达式：形如 `{ ... }`。"""
    arg_types = {"this": True, "uuid": False}

    @property
    def id(self) -> str:
        """占位符生成的唯一编号。"""
        return self.args.get("uuid", "")


class CustomDialect(Dialect):
    """
    自定义方言：
      - Parser: 识别 `{ ... }` 并转成 Brace
      - Generator: 将 Brace 输出为 `{inner_sql}`
    """

    class Tokenizer(sqlglot.tokens.Tokenizer):
        # 暂时沿用默认 Tokenizer
        ...

    class Parser(sqlglot.parser.Parser):
        def _parse_primary(self):
            # 捕获 `{`
            if self._match(TokenType.L_BRACE):
                inner = self._parse_expression()
                if not self._match(TokenType.R_BRACE):
                    self.raise_error("Expecting '}'")
                # 包装成 Brace，占位符带上 uuid
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

    # 新增的更丰富结构
    exp.Alias,          # COUNT(*) AS AthleteCount
    exp.Star,           # COUNT(*)
    exp.And,            # Year > 2016 AND Age > {older}
    exp.Limit,          # LIMIT 3 / LIMIT {n}
    exp.GT,             # >
    exp.GTE,            # >=
    exp.LT,             # <
    exp.LTE,            # <=

    # 必须包含 Brace，否则会在 AST 白名单里被判非法
    Brace,
}


def _ensure_uuid(node: exp.Expression) -> str:
    """为节点补 uuid（如果还没有），并返回最终 uuid。"""
    uid = node.args.get("uuid")
    if uid:
        return uid
    uid = str(uuid.uuid4())
    node.set("uuid", uid)
    return uid


def _seed_initial_uuids(tree: exp.Expression) -> None:
    """
    给 tree 中需要跟踪替换/解析的节点补齐 uuid（仅缺失时补）：
      - Brace 占位符
      - Literal（含字符串/数字等字面量）
      - IN 节点（作为 IN 组级别 uuid）

    规则：
      - 对 IN 列表，IN 节点与其 expressions 共享同一个 uuid（组级 uuid）。
    """
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
            # IN 列表成员统一使用 IN 组 uuid
            if not node.args.get("uuid"):
                node.set("uuid", _ensure_uuid(parent))
            continue
        _ensure_uuid(node)


def _check_node(node: exp.Expression):
    """
    递归检查 AST，所有节点类型必须在 ALLOWED_NODE_TYPES 白名单内。
    """
    if type(node) not in ALLOWED_NODE_TYPES:
        raise DisallowedNodeError(f"Disallowed node type detected: {type(node).__name__}")

    for arg in node.args.values():
        if isinstance(arg, list):
            for c in arg:
                if isinstance(c, exp.Expression):
                    _check_node(c)
        elif isinstance(arg, exp.Expression):
            _check_node(arg)


def _check_placeholder_positions(tree: exp.Expression):
    """
    占位符位置规则（严格版）：

      1. 占位符必须出现在某个 SELECT 语句内部。
      2. 允许的四种上下文：
         - SELECT 投影列表里
         - GROUP BY 的分组键：如 GROUP BY {group_expr}
         - LIMIT：必须是 LIMIT {placeholder} 这种“直接参数”
         - WHERE：仅允许出现在比较右侧：B op {C}
             * 占位符必须在比较右边
             * op ∈ {>, >=, <, <=}，不允许 '='
      3. 其它位置一律不允许（包括 ORDER BY）。
    """
    infos: List[Dict[str, Any]] = []
    allowed_cmp_types = (exp.GT, exp.GTE, exp.LT, exp.LTE)

    for node in tree.find_all(Brace):
        # 1. 必须在 Select 里
        select_ancestor = node.find_ancestor(exp.Select)
        inner_sql = node.this.sql(dialect=CustomDialect) if node.this is not None else None
        if not select_ancestor:
            raise DisallowedNodeError("Placeholders must appear inside a SELECT statement")

        # 2. LIMIT 场景
        limit_ancestor = node.find_ancestor(exp.Limit)
        if limit_ancestor is not None:
            if node.parent is not limit_ancestor:
                raise DisallowedNodeError(
                    "A placeholder in LIMIT must be the direct parameter of LIMIT, e.g. LIMIT {n}"
                )
            parent = node.parent
            infos.append(
                {
                    "uuid": node.id,
                    "allowed_context": "Limit",
                    "inner_sql": inner_sql,    
                    "direct_parent": type(parent).__name__ if parent is not None else None,
                }
            )
            continue

        # 3. WHERE 场景（支持 AND / OR 嵌套）
        # 3. WHERE 场景（支持 AND / OR 嵌套）
        where_ancestor = node.find_ancestor(exp.Where)
        if where_ancestor is not None:
            # 找最近的比较节点
            cmp = node.find_ancestor(*allowed_cmp_types, exp.EQ)
            if cmp is None:
                raise DisallowedNodeError(
                    "A placeholder in WHERE must appear inside a comparison expression, e.g. B > {C}"
                )

            if not cmp.find_ancestor(exp.Where):
                raise DisallowedNodeError(
                    "A placeholder in WHERE must be part of a WHERE condition expression"
                )

            # 必须在右侧：B op {C}
            right = cmp.args.get("expression")
            if right is not node:
                raise DisallowedNodeError(
                    "Placeholders in WHERE must appear on the right side of the comparison, e.g. B > {C}"
                )

            if type(cmp) not in allowed_cmp_types:
                raise DisallowedNodeError(
                    "Comparisons containing placeholders may only use >, >=, <, <= — '=' is not allowed"
                )

            # ⭐ 新增：把左边的列名也拿出来
            left = cmp.this
            # 完整 SQL 形式（可能是 "t.year" 这种）
            left_sql = left.sql(dialect=CustomDialect) if isinstance(left, exp.Expression) else None

            # 如果你只想要纯列名，可以再做一点处理：
            left_col_name = None
            if isinstance(left, exp.Column):
                # sqlglot 的 Column 有 .name 属性，拿到的是不带表前缀的列名
                left_col_name = left.name
            elif isinstance(left, exp.Identifier):
                left_col_name = left.this

            parent = node.parent
            infos.append(
                {
                    "uuid": node.id,
                    "allowed_context": "WhereComparison",
                    "direct_parent": type(parent).__name__ if parent is not None else None,
                    "inner_sql": inner_sql,                       # {year_min} 里面的东西
                    "placeholder_sql": node.sql(dialect=CustomDialect),  # "{year_min}"
                    "where_left_sql": left_sql,                   # ⭐ WHERE 左边完整 SQL，比如 "year" 或 "t.year"
                    "where_left_col": left_col_name,              # ⭐ 纯列名，比如 "year"
                }
            )
            continue


        # 4. GROUP BY 场景
        group_ancestor = node.find_ancestor(exp.Group)
        if group_ancestor is not None:
            # 要求最终归属在 group_ancestor.args["expressions"] 中，作为一个合法分组键
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
                }
            )
            continue

        # 5. 默认：必须在 SELECT 投影里
        cur = node
        while cur.parent is not None and cur.parent is not select_ancestor:
            cur = cur.parent

        projections = select_ancestor.args.get("expressions") or []
        if cur not in projections:
            raise DisallowedNodeError(
                "Placeholders are only allowed in SELECT projection list, GROUP BY keys, "
                "LIMIT, or on the right-hand side of WHERE comparisons like B > {C}; "
                "they are not allowed in other locations (such as ORDER BY)."
            )

        parent = node.parent
        infos.append(
            {
                "uuid": node.id,
                "inner_sql": inner_sql,    
                "allowed_context": "Select",
                "direct_parent": type(parent).__name__ if parent is not None else None,
            }
        )

    return infos


def validate_sql_strict(sql: str) -> Tuple[exp.Expression, List[Dict[str, Any]]]:
    """
    直接用 CustomDialect 解析包含 {} 的 SQL，
    并做：
      1. AST 节点类型白名单校验
      2. 占位符位置合法性校验
      3. 为 Brace / Literal / IN 节点补齐 uuid（仅缺失时补）

    返回 (tree, placeholder_infos)；
    如有非法结构会抛 ParseError / DisallowedNodeError。
    """
    tree = parse_one(sql, read=CustomDialect)
    _check_node(tree)
    placeholder_infos = _check_placeholder_positions(tree)
    _seed_initial_uuids(tree)
    return tree, placeholder_infos


# --------------------------------------------------------------------------- #
#                             工具主入口类                                     #
# --------------------------------------------------------------------------- #

class BraceSQLToolkit:
    """支持 `{}` 占位符的 SQL 解析 / 校验 / 替换工具。"""

    # 对外暴露，保持原有 API
    Brace = Brace
    _BraceSQL = CustomDialect

    # --------------------------- 常量配置 ---------------------------------- #
    _ALLOWED_PRED = (exp.Binary, exp.In)

    # ----------------------------- 简单工具 -------------------------------- #
    def has_placeholder(self, sql: str) -> bool:
        """判断 SQL 中是否包含 {} 占位符。"""
        try:
            tree = self.parse(sql)
            return any(isinstance(n, self.Brace) for n in tree.walk())
        except ParseError:
            return False

    # ----------------------------- 公共 API -------------------------------- #
    def parse(self, sql: str) -> exp.Expression:
        """
        解析 SQL 字符串并返回 AST。
        这里直接调用严格校验的 parse，以保证树结构一定合法；
        如你只想“宽松解析”，可以改成 parse_one(..., read=self._BraceSQL)。
        """
        tree, _ = validate_sql_strict(sql)
        return tree

    def transpile(self, sql: str) -> str:
        """等价转译：解析后再生成 SQL，主要用于格式化。"""
        return self.parse(sql).sql(dialect=self._BraceSQL)

    def brace_locations(self, sql: str) -> list[tuple]:
        """返回占位符在 SELECT / WHERE 中出现的位置及 uuid。"""
        _, infos = validate_sql_strict(sql)
        return [(x["allowed_context"], x["uuid"]) for x in infos]

    # ------- 兼容旧接口：用新的严格校验实现 invalid_predicates / check ------- #
    def invalid_predicates(self, sql: str) -> List[Tuple[str, str]]:
        """
        原来的主校验入口，保留对外语义：
          - 返回 (错误标签, 错误信息) 列表。若为空即合法。
        现在内部委托给 validate_sql_strict。
        """
        errors: list[tuple[str, str]] = []
        try:
            validate_sql_strict(sql)
        except ParseError as e:
            errors.append(("SYNTAX", str(e).split("\n", 1)[0]))
        except DisallowedNodeError as e:
            errors.append(("VALIDATE", str(e)))
        return errors

    def check(self, sql: str, explain: bool = False) -> Tuple[bool, str | None]:
        """便捷封装：返回 (是否合法, 失败原因)。"""
        errs = self.invalid_predicates(sql)
        if errs:
            reason = "; ".join(f"[{tag}] {msg}" for tag, msg in errs) if explain else None
            return False, reason
        return True, None

    # ---------------------- 下方：你原来的“后半部分” ---------------------- #

    def substitute_select_placeholders_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, str | list[str]],
    ) -> str:
        """
        - 支持标量替换，也支持多值展开
        - 关键修复：当投影自身就是 Brace 节点时也参与替换
        """
        select: exp.Select = tree.find(exp.Select)
        new_projs: list[exp.Expression] = []

        def _expr_with_uid(x, uid: str):
            node = x if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)
            node.set("uuid", uid)
            return node

        for proj in select.expressions:
            # 把「根节点是 Brace」也纳入遍历范围
            braces = ([proj] if isinstance(proj, self.Brace) else []) + list(proj.find_all(self.Brace))
            seen_uid = set()
            braces = [b for b in braces if not (b.id in seen_uid or seen_uid.add(b.id))]

            # ---------- ① 标量替换 ----------
            for b in braces:
                uid, repl = b.id, replacements.get(b.id)
                if repl is not None and not isinstance(repl, list):
                    replacement_ast = _expr_with_uid(repl, uid)
                    if b is proj:
                        proj = replacement_ast
                    b.replace(replacement_ast)

            # ---------- ② 多值展开 ----------
            multi = [
                (b.id, [_expr_with_uid(v, b.id) for v in replacements[b.id]])
                for b in braces
                if b.id in replacements and isinstance(replacements[b.id], list)
            ]
            if not multi:
                new_projs.append(proj)
                continue

            keys, vals_list = zip(*multi)
            for combo in product(*vals_list):
                clone = proj.copy()

                # 逐个 uid → val 替换
                for uid, val in zip(keys, combo):
                    # 如果 clone 自身就是目标 Brace
                    if isinstance(clone, self.Brace) and clone.id == uid:
                        clone = val.copy()
                        continue
                    for b in clone.find_all(self.Brace):
                        if b.id == uid:
                            b.replace(val)
                new_projs.append(clone)

        select.set("expressions", new_projs)
        return tree.sql(dialect=self._BraceSQL)

    def substitute_where_range_placeholders_on_tree(
        self,
        tree: exp.Expression,
        replacements: dict[str, str | list[str]],
    ) -> str:
        """
        将 WHERE 子句里形如
            <column> OP {brace}
        的表达式，若占位符的替换值是 “a - b”，
        则改写成
            <column> BETWEEN a AND b
        只处理 Binary ( =, >, <, >=, <= 等) 且 {brace} 出现在右侧的情况。
        """
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)

        def _walk(node: exp.Expression):
            # 只关注真正的 Binary 谓词
            if isinstance(node, exp.Binary) and isinstance(node.expression, self.Brace):
                brace_node: Brace = node.expression
                uid = brace_node.id
                repl = replacements.get(uid)

                # 只处理形如 "2002 - 2010" 的区间
                if isinstance(repl, str) and "-" in repl:
                    low_str, high_str = [p.strip() for p in repl.split("-", 1)]
                    low = parse_one(low_str, read=self._BraceSQL)
                    high = parse_one(high_str, read=self._BraceSQL)
                    low.set("uuid", uid)
                    high.set("uuid", uid)

                    between = exp.Between(
                        this=node.this.copy(),   # 左边的列
                        low=low,
                        high=high,
                    )
                    between.set("uuid", uid)
                    node.replace(between)
                    return  # 二元节点已替换，无需再递归

            # 递归检查子表达式
            for child in node.iter_expressions():
                _walk(child)

        _walk(where)
        return tree.sql(dialect=self._BraceSQL)

    def parse_sql_to_json(self, sql_or_tree: Union[str, exp.Expression]) -> Dict[str, Any]:
        """
        将 WHERE 条件解析为结构化 JSON。

        为保证 uuid 稳定，推荐传入已经通过 validate_sql_strict / parse 得到的 tree；
        在同一棵 tree 上多次调用不会重置已有 uuid，只会补齐缺失 uuid。
        """
        # ---------- ① AST ----------
        tree = sql_or_tree if isinstance(sql_or_tree, exp.Expression) else self.parse(sql_or_tree)
        # 保证在同一棵 tree 上只补齐缺失 uuid，不会覆盖已有 uuid
        _seed_initial_uuids(tree)
        where: exp.Where | None = tree.find(exp.Where)
        if not where:
            return {"type": False}

        # ---------- ② 收集谓词（不再拆 IN） ----------
        def _collect_preds(node: exp.Expression):
            if isinstance(node, self._ALLOWED_PRED) and not isinstance(node, (exp.And, exp.Or)):
                yield node
            else:
                for child in node.iter_expressions():
                    yield from _collect_preds(child)

        # ---------- ③ 工具函数 ----------
        def _lit(node: exp.Expression) -> str:
            return node.sql(dialect=self._BraceSQL).strip("'\"{}")

        result: Dict[str, Any] = {"type": True}

        # ---------- ④ 扁平化 OR ----------
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

                # ---------- IN 谓词：一次性收集 ----------
                if isinstance(pred, exp.In):
                    group_uid = _ensure_uuid(pred)
                    vals = []
                    for lit in pred.expressions:
                        if isinstance(lit, exp.Expression):
                            lit.set("uuid", group_uid)
                        vals.append(_lit(lit))
                    vals.append(group_uid)  # 末尾放 IN 组级别 uuid
                    match_values.append([vals])

                # ---------- 其它谓词：保持旧逻辑 ----------
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
        """
        把
            <col> = <literal|Brace>(uuid=X)
        改成
            <col> IN (...)
        只有当 <uuid> 在 `replacements` 中且 value 为列表时才替换。
        """
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)
        _seed_initial_uuids(tree)

        def _expr(x):
            return x if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)

        def _walk(node: exp.Expression):
            # -------- IN 列表替换（你原来写的是 IN 分支在前，这里保持不动） ----------
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

            # -------- 递归 ----------
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
        """
        把
            <col> LIKE <literal|Brace>(uuid=X)
        改写成
            (<col> LIKE '%v1%' OR <col> LIKE '%v2%' ...)
        —— 仅当 <uuid> 在 `replacements` 中且 value 为列表时才替换
        —— 如 `wrap_wildcards=True`（默认），会自动在每个替换值两侧补 `%`
        """
        where = tree.find(exp.Where)
        if not where:
            return tree.sql(dialect=self._BraceSQL)
        _seed_initial_uuids(tree)

        def _expr(x):
            return x if isinstance(x, exp.Expression) else parse_one(x, read=self._BraceSQL)

        def _make_like(column_ast: exp.Expression, pattern_ast: exp.Expression, like_cls):
            return like_cls(this=column_ast.copy(), expression=pattern_ast)

        def _walk(node: exp.Expression):
            # ---------- 命中 LIKE / ILIKE ----------
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
