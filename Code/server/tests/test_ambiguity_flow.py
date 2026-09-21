import ast
from contextlib import redirect_stdout
from datetime import datetime
import io
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import Mock

import pandas as pd
from flask import Flask, jsonify, request
from sqlglot import exp, parse_one
from sqlglot.errors import ParseError


SERVER_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_DIR))

from function.brace_toolkit import (
    BraceSQLToolkit,
    DisallowedNodeError,
    validate_sql_strict,
    validate_tree_strict,
)
from function.final_uuid_result_handler import apply_final_uuid_result
from function.initial_fuzzy_recommendation import build_initial_fuzzy_recommendations


class AmbiguityFlowTests(unittest.TestCase):
    def setUp(self):
        # Load the real route bodies without importing models or starting workers.
        names = {
            "reset_globals", "submit", "fuzzytext", "generate_sql",
            "handle_fully_resolvable_text", "parse_sql_to_json",
            "build_uuid_match_map", "run_followups", "handle_sql_error",
        }
        source = ast.parse((SERVER_DIR / "app.py").read_text())
        functions = []
        for node in source.body:
            if isinstance(node, ast.FunctionDef) and node.name in names:
                node.decorator_list = []
                functions.append(node)
        self.assertEqual({node.name for node in functions}, names)
        self.context = {
            "pd": pd, "json": json, "re": re, "datetime": datetime, "exp": exp,
            "jsonify": jsonify, "request": request,
            "BraceSQLToolkit": BraceSQLToolkit,
            "DisallowedNodeError": DisallowedNodeError,
            "ParseError": ParseError,
            "validate_sql_strict": validate_sql_strict,
            "validate_tree_strict": validate_tree_strict,
            "apply_final_uuid_result": apply_final_uuid_result,
            "df": pd.DataFrame({
                "Price": [10, 20], "Quantity": [2, 3],
                "Country": ["US", "CA"], "City": ["Boston", "Toronto"],
            }),
            "file_name": "sales", "unit": {},
            "Ambigioussql": Mock(), "ReGeneratsql": Mock(), "Colfuzzy": Mock(),
            "embedding_event": Mock(),
            "build_translation_sentence": Mock(return_value={
                "translated_question": "Review the query.",
                "initial_fuzzy_recommendations": {},
            }),
            "generate_visual_recommendations": Mock(return_value={"data": []}),
        }
        module = ast.Module(body=functions, type_ignores=[])
        exec(compile(module, str(SERVER_DIR / "app.py"), "exec"), self.context)
        app = Flask(__name__)
        app.config["TESTING"] = True
        for path, name in (
            ("/gettext", "submit"),
            ("/api/fuzzytext", "fuzzytext"),
            ("/api/runfollowups", "run_followups"),
        ):
            app.add_url_rule(path, name, self.context[name], methods=["POST"])
        for error in (DisallowedNodeError, ParseError):
            app.register_error_handler(error, self.context["handle_sql_error"])
        self.client = app.test_client()
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def submit_sql(self, sql, candidates=None):
        self.context["Ambigioussql"].return_value.Generatsql.return_value = sql
        if candidates is not None:
            self.context["Colfuzzy"].return_value.Generation.return_value = json.dumps(candidates)
        return self.client.post("/gettext", json={"text": "Analyze the sales table."})

    def select_columns(self, key, values):
        return self.client.post("/api/fuzzytext", json={
            "keyName": key,
            "category": "multiple_column",
            "userInput": json.dumps(values),
        })

    def only_recommendation(self, response):
        self.assertEqual(response.status_code, 200)
        recommendations = response.get_json()["textrecommend"]
        self.assertEqual(len(recommendations), 1)
        return next(iter(recommendations.items()))

    def test_max_recommends_one_single_select_control(self):
        response = self.submit_sql("SELECT MAX({amount}) FROM sales", ["Price", "Quantity"])
        _, detail = self.only_recommendation(response)
        self.assertTrue(detail["single_select"])
        self.context["Colfuzzy"].return_value.Generation.assert_called_once()

    def test_select_and_group_share_one_recommendation_and_uuid(self):
        response = self.submit_sql(
            "SELECT {region}, COUNT(*) FROM sales GROUP BY {region}",
            ["Country", "City"],
        )
        key, detail = self.only_recommendation(response)
        self.assertTrue(detail["single_select"])
        self.context["Colfuzzy"].return_value.Generation.assert_called_once()
        _, infos = validate_tree_strict(self.context["tree"])
        self.assertEqual(len(infos), 2)
        self.assertEqual({info["uuid"] for info in infos}, {key.split("+")[-1]})

    def test_initial_single_choice_updates_select_and_group(self):
        response = self.submit_sql(
            "SELECT {region}, COUNT(*) FROM sales GROUP BY {region}", ["Country"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["awaitingFollowup"])
        tree = self.context["tree"]
        self.assertEqual(tree.expressions[0].name, "Country")
        self.assertEqual(tree.args["group"].expressions[0].name, "Country")
        self.assertFalse(list(tree.find_all(BraceSQLToolkit.Brace)))

    def test_first_selection_rejects_multiple_or_unknown_columns(self):
        response = self.submit_sql("SELECT MAX({amount}) FROM sales", ["Price", "Quantity"])
        key, _ = self.only_recommendation(response)
        for values in (["Price", "Quantity"], [], ["Missing"]):
            with self.subTest(values=values):
                rejected = self.select_columns(key, values)
                self.assertEqual(rejected.status_code, 400)
                self.assertFalse(self.context["check_fuzzy_text"][key])

    def test_final_edit_keeps_max_and_alias(self):
        response = self.submit_sql(
            "SELECT MAX({amount}) AS Peak FROM sales", ["Price", "Quantity"],
        )
        key, _ = self.only_recommendation(response)
        self.assertEqual(self.select_columns(key, ["Price"]).status_code, 200)
        self.assertEqual(self.context["tree"].find(exp.Max).this.name, "Price")
        response = self.client.post("/api/runfollowups", json=[{key.split("+")[-1]: ["Quantity"]}])
        self.assertEqual(response.status_code, 200)
        sql = self.context["generate_visual_recommendations"].call_args.kwargs["sql_query"]
        result = parse_one(sql)
        self.assertEqual(result.find(exp.Max).this.name, "Quantity")
        self.assertEqual(result.expressions[0].alias, "Peak")

    def test_final_edit_updates_select_and_group_together(self):
        response = self.submit_sql(
            "SELECT {region}, COUNT(*) FROM sales GROUP BY {region}",
            ["Country", "City"],
        )
        key, _ = self.only_recommendation(response)
        self.assertEqual(self.select_columns(key, ["Country"]).status_code, 200)
        response = self.client.post("/api/runfollowups", json=[{key.split("+")[-1]: ["City"]}])
        self.assertEqual(response.status_code, 200)
        sql = self.context["generate_visual_recommendations"].call_args.kwargs["sql_query"]
        result = parse_one(sql)
        self.assertEqual(result.expressions[0].name, "City")
        self.assertEqual(result.args["group"].expressions[0].name, "City")

    def test_max_special_column_names_are_quoted_on_initial_and_final_choice(self):
        self.context["df"]["Gold Medal"] = [1, 2]
        self.context["df"]["Cost-Adjusted"] = [3, 4]
        response = self.submit_sql(
            "SELECT MAX({amount}) AS Peak FROM sales", ["Gold Medal", "Cost-Adjusted"],
        )
        key, _ = self.only_recommendation(response)
        self.assertEqual(self.select_columns(key, ["Gold Medal"]).status_code, 200)
        initial = self.context["tree"].find(exp.Max).this
        self.assertEqual(initial.name, "Gold Medal")
        self.assertTrue(initial.this.args["quoted"])
        response = self.client.post(
            "/api/runfollowups", json=[{key.split("+")[-1]: ["Cost-Adjusted"]}],
        )
        self.assertEqual(response.status_code, 200)
        sql = self.context["generate_visual_recommendations"].call_args.kwargs["sql_query"]
        result = parse_one(sql)
        self.assertEqual(result.find(exp.Max).this.name, "Cost-Adjusted")
        self.assertTrue(result.find(exp.Max).this.this.args["quoted"])
        self.assertEqual(result.expressions[0].alias, "Peak")

    def test_group_special_column_names_remain_shared_on_final_choice(self):
        self.context["df"]["Gold Medal"] = [1, 2]
        self.context["df"]["Cost-Adjusted"] = [3, 4]
        response = self.submit_sql(
            "SELECT {region}, COUNT(*) FROM sales GROUP BY {region}",
            ["Gold Medal", "Cost-Adjusted"],
        )
        key, _ = self.only_recommendation(response)
        self.assertEqual(self.select_columns(key, ["Gold Medal"]).status_code, 200)
        tree = self.context["tree"]
        for column in (tree.expressions[0], tree.args["group"].expressions[0]):
            self.assertEqual(column.name, "Gold Medal")
            self.assertTrue(column.this.args["quoted"])
        response = self.client.post(
            "/api/runfollowups", json=[{key.split("+")[-1]: ["Cost-Adjusted"]}],
        )
        self.assertEqual(response.status_code, 200)
        sql = self.context["generate_visual_recommendations"].call_args.kwargs["sql_query"]
        result = parse_one(sql)
        for column in (result.expressions[0], result.args["group"].expressions[0]):
            self.assertEqual(column.name, "Cost-Adjusted")
            self.assertTrue(column.this.args["quoted"])

    def test_only_candidate_with_special_name_is_inserted_as_column(self):
        self.context["df"]["Cost-Adjusted"] = [3, 4]
        response = self.submit_sql("SELECT MAX({amount}) FROM sales", ["Cost-Adjusted"])
        self.assertEqual(response.status_code, 200)
        column = self.context["tree"].find(exp.Max).this
        self.assertIsInstance(column, exp.Column)
        self.assertEqual(column.name, "Cost-Adjusted")
        self.assertTrue(column.this.args["quoted"])

    def test_final_selection_rejects_multiple_columns(self):
        response = self.submit_sql("SELECT MAX({amount}) FROM sales", ["Price", "Quantity"])
        key, _ = self.only_recommendation(response)
        self.assertEqual(self.select_columns(key, ["Price"]).status_code, 200)
        response = self.client.post(
            "/api/runfollowups", json=[{key.split("+")[-1]: ["Price", "Quantity"]}],
        )
        self.assertEqual(response.status_code, 400)
        self.context["generate_visual_recommendations"].assert_not_called()
        self.assertEqual(self.context["tree"].find(exp.Max).this.name, "Price")

    def test_plain_select_still_accepts_multiple_columns(self):
        response = self.submit_sql("SELECT {amount} FROM sales", ["Price", "Quantity"])
        key, detail = self.only_recommendation(response)
        self.assertFalse(detail["single_select"])
        self.assertEqual(self.select_columns(key, ["Price", "Quantity"]).status_code, 200)
        self.assertEqual([column.name for column in self.context["tree"].expressions], ["Price", "Quantity"])

    def test_invalid_selection_keeps_original_tree_and_can_be_corrected(self):
        response = self.submit_sql("SELECT {amount} FROM sales", ["Price", "Quantity"])
        key, _ = self.only_recommendation(response)
        original = self.context["tree"]
        original_sql = original.sql(dialect=BraceSQLToolkit._BraceSQL)
        response = self.select_columns(key, ["MAX(Price) OVER ()"])
        self.assertEqual(response.status_code, 400)
        self.assertIs(self.context["tree"], original)
        self.assertEqual(self.context["tree"].sql(dialect=BraceSQLToolkit._BraceSQL), original_sql)
        self.assertTrue(list(self.context["tree"].find_all(BraceSQLToolkit.Brace)))
        response = self.select_columns(key, ["Quantity"])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["awaitingFollowup"])
        self.assertEqual(self.context["tree"].expressions[0].name, "Quantity")
        self.assertFalse(list(self.context["tree"].find_all(BraceSQLToolkit.Brace)))

    def test_calculation_and_empty_final_edits_keep_query(self):
        response = self.submit_sql("SELECT Price * Quantity AS Revenue FROM sales")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["awaitingFollowup"])
        tree = self.context["tree"]
        self.assertIs(apply_final_uuid_result([], tree, {}, {}), tree)
        response = self.client.post("/api/runfollowups", json=[])
        self.assertEqual(response.status_code, 200)
        sql = self.context["generate_visual_recommendations"].call_args.kwargs["sql_query"]
        result = parse_one(sql)
        self.assertIsInstance(result.expressions[0].this, exp.Mul)
        self.assertEqual(result.expressions[0].alias, "Revenue")

    def test_invalid_initial_sql_retries_with_original_sql(self):
        original = "SELECT Price FROM sales WHERE 'US' = Country"
        corrected = "SELECT Price FROM sales"
        regenerate = self.context["ReGeneratsql"].return_value.Generate
        regenerate.return_value = corrected
        response = self.submit_sql(original)
        self.assertEqual(response.status_code, 200)
        regenerate.assert_called_once()
        self.assertEqual(regenerate.call_args.kwargs["sql"], original)
        self.assertIsInstance(regenerate.call_args.kwargs["syntax_error"], DisallowedNodeError)
        self.assertEqual(self.context["tree"].sql(), corrected)

    def test_single_select_metadata_reaches_followup_choices(self):
        response = self.submit_sql("SELECT MAX({amount}) FROM sales", ["Price", "Quantity"])
        key, _ = self.only_recommendation(response)
        result = build_initial_fuzzy_recommendations(self.context["textrecommend"], {})
        self.assertEqual(result[key.split("+")[-1]], {
            "options": ["Price", "Quantity"], "single_select": True,
        })


if __name__ == "__main__":
    unittest.main()
