import sys
import unittest
from pathlib import Path

from sqlglot import exp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from function.brace_toolkit import (
    Brace,
    BraceSQLToolkit,
    CustomDialect,
    DisallowedNodeError,
    validate_sql_strict,
    validate_tree_strict,
)


class BraceSQLToolkitTests(unittest.TestCase):
    def setUp(self):
        self.toolkit = BraceSQLToolkit()
        self.columns = ["Price", "Quantity", "Genre", "Age", "Year"]

    def test_calculations_and_ordinary_aggregates_remain_supported(self):
        sql = (
            "SELECT Price * Quantity AS Revenue, SUM(Price * Quantity), "
            "MIN(Price), MAX(Price), AVG(Price), COUNT(*) FROM sales "
            "WHERE (Price >= -5 AND Quantity IN (1, 2)) "
            "OR Price BETWEEN -10 AND 20 "
            "GROUP BY Price * Quantity ORDER BY Revenue LIMIT 3"
        )
        tree, infos = validate_sql_strict(sql, self.columns)
        self.assertFalse(infos)
        self.assertEqual(len(tree.expressions), 6)
        self.assertIn("SUM(Price * Quantity)", tree.sql(dialect=CustomDialect))

    def test_where_rejects_reversed_columns_and_non_values(self):
        predicates = [
            "'Comedy' = Genre",
            "Comedy = Genre",
            "Age > Year",
            "1 = 1",
            "Age + 1 > 20",
            "Age > 1 + 2",
            "1 > {older}",
            "Age + 1 > {older}",
            "Genre LIKE Genre",
            "Age IN (1, Year)",
            "Age BETWEEN 18 AND Year",
        ]
        for predicate in predicates:
            with self.subTest(predicate=predicate):
                with self.assertRaises(DisallowedNodeError):
                    validate_sql_strict(f"SELECT Age FROM sales WHERE {predicate}", self.columns)

    def test_where_schema_check_is_optional_and_case_insensitive(self):
        tree, _ = validate_sql_strict("SELECT Missing FROM sales WHERE AGE > -10", self.columns)
        self.assertEqual(tree.find(exp.Where).this.this.name, "Age")
        _, infos = validate_sql_strict("SELECT Age FROM sales WHERE AGE > {older}", self.columns)
        self.assertEqual(infos[0]["where_left_col"], "Age")
        validate_sql_strict("SELECT Age FROM sales WHERE Missing > 1")
        with self.assertRaisesRegex(DisallowedNodeError, "Unknown column"):
            validate_sql_strict("SELECT Age FROM sales WHERE Missing > 1", self.columns)

    def test_where_literals_ranges_and_logic_are_supported(self):
        validate_sql_strict(
            "SELECT Age FROM sales WHERE "
            "(Genre = 'Comedy' OR Genre LIKE '%Drama%') "
            "AND Age IN (-1, 20) AND Price BETWEEN -10.5 AND 30 "
            "AND Quantity > (-2)",
            self.columns,
        )

    def test_where_placeholders_keep_existing_range_only_rules(self):
        tree, infos = validate_sql_strict("SELECT Age FROM sales WHERE Age > {older}", self.columns)
        self.assertEqual(infos[0]["where_left_col"], "Age")
        self.assertIsNotNone(tree.find(Brace))
        for predicate in ("Age = {older}", "Age IN ({older})", "Genre LIKE {genre}"):
            with self.subTest(predicate=predicate):
                with self.assertRaises(DisallowedNodeError):
                    validate_sql_strict(f"SELECT Age FROM sales WHERE {predicate}", self.columns)

    def test_resolved_where_range_can_be_revalidated(self):
        tree, infos = validate_sql_strict("SELECT Age FROM sales WHERE Age > {older}", self.columns)
        uid = infos[0]["uuid"]
        result = self.toolkit.substitute_where_range_placeholders_on_tree(tree, {uid: "18-30"})
        self.assertEqual(result, "SELECT Age FROM sales WHERE Age BETWEEN 18 AND 30")
        checked_tree, checked_infos = validate_tree_strict(tree, self.columns)
        self.assertIs(checked_tree, tree)
        self.assertFalse(checked_infos)
        self.assertEqual(tree.find(exp.Between).args["uuid"], uid)

    def test_aggregate_placeholders_require_one_column(self):
        for aggregate in ("MAX", "SUM", "MIN", "AVG", "COUNT"):
            with self.subTest(aggregate=aggregate):
                tree, infos = validate_sql_strict(f"SELECT {aggregate}({{measure}}) FROM sales")
                uid = infos[0]["uuid"]
                self.assertTrue(infos[0]["single_select"])
                with self.assertRaises(DisallowedNodeError):
                    self.toolkit.substitute_select_placeholders_on_tree(tree, {uid: ["Price", "Quantity"]})
                result = self.toolkit.substitute_select_placeholders_on_tree(tree, {uid: ["Price"]})
                self.assertEqual(result, f"SELECT {aggregate}(Price) FROM sales")
                self.assertEqual(tree.find(exp.Column).args["uuid"], uid)

    def test_select_group_and_aggregate_share_one_selection(self):
        tree, infos = validate_sql_strict(
            "SELECT {measure}, SUM({measure}) FROM sales GROUP BY {measure}"
        )
        self.assertEqual(len({info["uuid"] for info in infos}), 1)
        self.assertTrue(all(info["single_select"] for info in infos))
        uid = infos[0]["uuid"]
        before = tree.sql(dialect=CustomDialect)
        with self.assertRaises(DisallowedNodeError):
            self.toolkit.substitute_select_placeholders_on_tree(tree, {uid: ["Price", "Quantity"]})
        self.assertEqual(tree.sql(dialect=CustomDialect), before)
        result = self.toolkit.substitute_select_placeholders_on_tree(tree, {uid: "Price"})
        self.assertEqual(result, "SELECT Price, SUM(Price) FROM sales GROUP BY Price")
        self.assertEqual(len(list(tree.find_all(Brace))), 0)
        self.assertTrue(all(column.args["uuid"] == uid for column in tree.find_all(exp.Column)))

    def test_group_only_placeholder_is_replaced(self):
        tree, infos = validate_sql_strict("SELECT COUNT(*) FROM sales GROUP BY {category}")
        self.assertEqual(infos[0]["allowed_context"], "GroupBy")
        self.assertTrue(infos[0]["single_select"])
        result = self.toolkit.substitute_select_placeholders_on_tree(tree, {infos[0]["uuid"]: ["Genre"]})
        self.assertEqual(result, "SELECT COUNT(*) FROM sales GROUP BY Genre")

    def test_direct_select_still_supports_multiple_columns(self):
        tree, infos = validate_sql_strict("SELECT {measure} FROM sales")
        self.assertFalse(infos[0]["single_select"])
        result = self.toolkit.substitute_select_placeholders_on_tree(
            tree, {infos[0]["uuid"]: ["Price", "Quantity"]}
        )
        self.assertEqual(result, "SELECT Price, Quantity FROM sales")

    def test_repeated_placeholder_inside_calculation_is_replaced_everywhere(self):
        tree, infos = validate_sql_strict("SELECT {measure} + {measure} FROM sales")
        uid = infos[0]["uuid"]
        result = self.toolkit.substitute_select_placeholders_on_tree(tree, {uid: "Price"})
        self.assertEqual(result, "SELECT Price + Price FROM sales")

    def test_where_placeholder_does_not_share_column_placeholder_uuid(self):
        tree, infos = validate_sql_strict(
            "SELECT SUM({measure}) FROM sales WHERE Price > {measure}", self.columns
        )
        self.assertEqual(len({info["uuid"] for info in infos}), 2)
        column_info = next(info for info in infos if info["allowed_context"] == "Select")
        result = self.toolkit.substitute_select_placeholders_on_tree(
            tree, {column_info["uuid"]: "Quantity"}
        )
        self.assertEqual(result, "SELECT SUM(Quantity) FROM sales WHERE Price > {measure}")

    def test_tree_revalidation_preserves_identity_and_uuids(self):
        tree, infos = validate_sql_strict(
            "SELECT {measure}, SUM({measure}) FROM sales WHERE Price > 10 GROUP BY {measure}"
        )
        before = [node.args.get("uuid") for node in tree.walk()]
        checked_tree, checked_infos = validate_tree_strict(tree, self.columns)
        self.assertIs(checked_tree, tree)
        self.assertEqual(before, [node.args.get("uuid") for node in tree.walk()])
        self.assertEqual(infos, checked_infos)

    def test_limit_placeholder_is_rejected_but_numeric_limit_remains(self):
        validate_sql_strict("SELECT Age FROM sales LIMIT 3")
        with self.assertRaisesRegex(DisallowedNodeError, "LIMIT"):
            validate_sql_strict("SELECT Age FROM sales LIMIT {few}")


if __name__ == "__main__":
    unittest.main()
