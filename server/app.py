import ast
import copy
import json
import os
import re
import sys
import threading
import uuid
from datetime import datetime

import duckdb  # type: ignore
import pandas as pd
from flask import Flask, jsonify, request
from sqlglot import exp, parse_one
from sqlglot.errors import ParseError

from function.brace_toolkit import BraceSQLToolkit, DisallowedNodeError, validate_sql_strict
from function.changechart import Changechart
from function.changeinsight5 import ChangeInsight5
from function.colfuzzy import Colfuzzy
from function.dataanalyze import DataAnalyzer
from function.divide import Divide
from function.documentembedder import DocumentEmbedder
from function.documentsearcher import DocumentSearcher
from function.final_uuid_result_handler import apply_final_uuid_result
from function.insight2 import Insight2
from function.initial_fuzzy_recommendation import build_initial_fuzzy_recommendations
from function.likeexact import LikeExact
from function.phase import Phase
from function.regenerate import ReGeneratsql
from function.sql_ambigious import Ambigioussql
from function.stringcheck import StringCheckMeaning
from function.textContent import TextContent
from function.translate import Translate
from function.visualrecommendation import VisualRecommend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__)


goal = ""  
df = None  
file_name = None
sql = None
string_encoding = {}
string_embeddings_dict = {}
column_names = None
unit = {}
allvisresult = {}

check_fuzzy_text = {}
textsolution = {}
textrecommend = {}
description = {}

check_fuzzy_string = {}
stringsolution = {}
stringrecommend = {}
tree= None  

embedding_event = threading.Event()
toolkit=None
parse_result=None



def drop_limit1(sql: str, *, dialect: str | None = None) -> str:
    tree1 = parse_one(sql, dialect=dialect)

    def _strip_limit1(node: exp.Expression) -> exp.Expression | None:
        
        if isinstance(node, exp.Limit):
            lit = node.expression
            if (
                isinstance(lit, exp.Literal)
                and lit.is_number
                and lit.this == "1"
            ):
                return None      
        return node              

    def _drop_ungrouped_min_max(node: exp.Expression) -> exp.Expression:
        
        if isinstance(node, (exp.Max, exp.Min)):
            
            if node.args.get("over"):
                return node

            sel = node.find_ancestor(exp.Select)
         
            if sel is not None and not sel.args.get("group"):
                arg = node.this
                if isinstance(arg, exp.Expression):
                    return arg.copy()
        return node

    
    new_tree = tree1.transform(_strip_limit1).transform(_drop_ungrouped_min_max)
    return new_tree.sql(dialect=dialect)
def column_summary(df, column_name):
    template = (
        'The "{column_name}" column contains {count} entries with a mean of {mean:.2f}, '
        'a median of {median}, a minimum value of {min}, and a maximum value of {max}. '
        'The standard deviation is {std:.2f}, indicating a spread of {column_name_lower} over a period.'
    )

    col = df[column_name]
    description = template.format(
        column_name=column_name,
        column_name_lower=column_name.lower(),
        count=col.count(),
        mean=col.mean(),
        median=col.median(),
        min=col.min(),
        max=col.max(),
        std=col.std()
    )

    return description

def reset_globals():
    global goal, sql, string_encoding, string_embeddings_dict, column_names, unit, tree,parse_result
    global check_fuzzy_text, textsolution, textrecommend, check_fuzzy_string, stringsolution, stringrecommend
    goal = ""  
    sql = None
    tree= None 
    parse_result = None
    
    check_fuzzy_text = {}
    textsolution = {}
    textrecommend = {}
    
    check_fuzzy_string = {}
    stringsolution = {}
    stringrecommend = {}


def build_translation_sentence(original_question: str, sql_query: str, tree=None) -> dict:
    
    translate_instance = Translate(df, file_name)
    translated_question = translate_instance.Final(
        orginalquestion=original_question,
        sql=sql_query,
        tree=tree,
    )
    if translated_question is None or str(translated_question).strip() == "":
        translated_question = original_question
    recommendation_payload = build_initial_fuzzy_recommendations(
        text_recommend=textrecommend,
        string_recommend=stringrecommend,
    )
    return {
        "translated_question": translated_question,
        "initial_fuzzy_recommendations": recommendation_payload,
    }



def process_embeddings(df):
    
    global string_embeddings_dict
    
    is_string = df.apply(lambda col: col.apply(lambda x: isinstance(x, str)).all())
    columns_that_are_strings = is_string.index[is_string].tolist()
    print("String columns found:", columns_that_are_strings)

    embedder = DocumentEmbedder(model_name="all-mpnet-base-v2", device="mps")
    embedder.load_documents(df[columns_that_are_strings])
    embedder.encode_documents()
    embeddings_dict = embedder.get_embeddings()
    string_embeddings_dict = embeddings_dict

    for col, emb in embeddings_dict.items():
        print(f"Column: {col}\nEmbeddings shape: {emb.shape}\n")

    embedding_event.set()


def generate_visual_recommendations(question, sql_query):
    
    divide_instance = Divide(df, file_name)
    divide_result = divide_instance.Generate(
        question=question, sql=sql_query, unit=unit
    )
    vis_result = {}
    print(divide_result)
    divide_result['sql'] = sql_query
    divide_result = {'1': divide_result}

    for _, value in divide_result.items():
        unique_key = str(uuid.uuid4())
        description = value.get("description")
        question_sub = value.get("question")
        sql_sub = value.get("sql")
        sql_sub=drop_limit1(sql_sub)
        print(sql_sub)        
        duckdb_conn = duckdb.connect()
        duckdb_conn.register(file_name, df)
        result_df = duckdb_conn.execute(sql_sub).df()
        print(result_df.head())

        visual_instance = VisualRecommend(result_df, file_name)
        vis_rec = visual_instance.Recommend(question=question_sub)
        # vis_rec["data"]["values"] = df.to_dict(orient='records')

        vis_result[unique_key] = {
            "description": description,
            "question": question_sub,
            "VisualRecommend_instance_result": vis_rec,
            "result_df": result_df,
            "sql": sql_sub,
        }
        print(type(vis_rec))

    for key, chart in vis_result.items():
        spec = chart.get("VisualRecommend_instance_result")
        if spec:
            modified_spec = add_basic_interactive_features(spec)
            vis_result[key]["VisualRecommend_instance_result"] = modified_spec
        allvisresult[key] = copy.deepcopy(vis_result[key])
    for key, chart in vis_result.items():
        spec = chart.get("VisualRecommend_instance_result")
        insight_instance = Insight2(chart.get("result_df"), file_name)
        insight_instance_result = insight_instance.story(
            question=goal, vegalite_spec=spec, all_file=df
        )
        while insight_instance_result is None:
            insight_instance_result = insight_instance.story(
            question=goal, vegalite_spec=spec, all_file=df
        )
            
        chart.pop("result_df")
        insight_instance_result = [
            {"key": k, "value": v} for k, v in insight_instance_result.items()
        ]
        vis_result[key]["insight"] = insight_instance_result
    print(len(vis_result))
    print(vis_result)
    now = datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M:%S"))
    return vis_result

def generate_sql(tree, textsolution):
    print("textsolution",textsolution)
    for key, value in textsolution.items():
        print(f"{key}: {value}")
        parts = key.split('+')
        if(parts[1]=='SELECT'):
            print(parts)
            print(value)

            toolkit.substitute_select_placeholders_on_tree(
            tree,
            {
                parts[2]: value,
            },

        )
        elif(parts[1]=='where1'):
            replacements = { parts[2]: value,}

            toolkit.substitute_where_range_placeholders_on_tree(tree, replacements)
    print("Updated tree:", tree)
    print("Updated type:", type(tree))
    return tree

def build_uuid_match_map(parse_result: dict) -> dict[str, str]:
    
    uuid2match = {}

    
    for key, triple in parse_result.items():
        if key.startswith("type"):
            continue



        match_types = triple[1][0]          
        value_uuid_pairs = triple[2]        

        
        for m_type, pair in zip(match_types, value_uuid_pairs):
            uuid = pair[0][-1]               
            uuid2match[uuid] = m_type
    print(uuid2match)
    return uuid2match

def handle_fully_resolvable_text():
    
    global toolkit ,tree, check_fuzzy_string ,parse_result

    print(textsolution)
    synthesized_tree = generate_sql(tree, textsolution)
    print("synthesized_tree", synthesized_tree)
    synthesized_sql=synthesized_tree.sql()
    print(synthesized_sql)

    toolkit = BraceSQLToolkit()
    parse_result = parse_sql_to_json(synthesized_tree)
    print("parse_result", parse_result)
    return synthesized_sql, parse_result


def process_fuzzy_string(parse_result):
    
    
    
    print("parse_result", parse_result)
    i = 0
    while f'condition_{i}' in parse_result:
        current_condition = parse_result[f'condition_{i}']
        phaseresult=Phase.Generate( goal=goal,sql=sql,Condition=current_condition)
        print(f'condition_{i}:', current_condition)
        parse_result[phaseresult] = parse_result.pop(f'condition_{i}')
        i += 1

    print("parse_result", parse_result)

    for k, value in parse_result.items():
        if k == "type":
            continue
        
        headers = value[0][0]
        match_types = value[1][0]
        values_list = value[2]
        print(headers)
        print(match_types)
        print(values_list)
        original_k = k 

        for header, match, val in zip(headers, match_types, values_list):
       
          
            k=original_k+'+'+val[0][-1]

            
            if match == "Exact Matching":
                print(f"Exact Matching for column: {header}")
                if(pd.api.types.is_numeric_dtype(df[header])):
                    continue
                
                
                searcher = DocumentSearcher(
                    model_name="all-mpnet-base-v2", device="mps"
                )
                searcher.set_document_embeddings(
                    documents=df[header].tolist(),
                    embeddings=string_embeddings_dict[header],
                )
                similarityresult = searcher.search(f"{val}")
                print("Search Results:")
                for i, doc in enumerate(similarityresult, 1):
                    print(f"{i}. {doc}")

                stringcheck_instance = StringCheckMeaning(df, file_name)
                check_result = stringcheck_instance.CheckMeaning(
                    sql=sql,
                    question=goal,
                    column_name=header,
                    column_value=f"{val}",
                    list=similarityresult[0:40],
                )

                print("Check Meaning Result:", check_result)

                if check_result["flag"]:
                    if len(check_result["Fuzzy_List"]) <= 1:
                        stringsolution.setdefault(k, {})[header] = {
                            "original": f"{val}"
                        }
                        stringsolution[k][header]["final"] = check_result["Fuzzy_List"]
                    else:
                        
                        stringsolution.setdefault(k, {})[header] = {
                            "original": f"{val}"
                        }
                        if k not in stringrecommend:
                            stringrecommend[k] = {}
                        stringrecommend[k][header] = {}
                        stringrecommend[k][header]["solution"] = check_result[
                            "Fuzzy_List"
                        ]
                        if k not in check_fuzzy_string:
                            check_fuzzy_string[k] = {}
                        check_fuzzy_string[k][header] = False

                        print("sbvv", stringrecommend)
                else:
                    print("完全没有和用户相近的词语")

            else:
                print(f"Fuzzy Matching for column: {header}")
                searcher = DocumentSearcher(
                    model_name="all-mpnet-base-v2", device="mps"
                )
                searcher.set_document_embeddings(
                    documents=df[header].tolist(),
                    embeddings=string_embeddings_dict[header],
                )
                similarityresult = searcher.search(f"{val}")
                print("Search Results:")

                for i, doc in enumerate(similarityresult, 1):
                    print(f"{i}. {doc}")



                likeexact_instance = LikeExact(df, file_name)
                likeexact_instance_result = likeexact_instance.CheckMeaning(
                    sql=sql,
                    question=goal,
                    column_name=header,
                    column_value=f"{val}",
                    list=similarityresult[0:40],
                )
                print("Check Meaning Result:", likeexact_instance_result)
                likeexact_instance_result_solution = list(
                    set(likeexact_instance_result["Extract"])
                )
                if len(likeexact_instance_result_solution) > 1:
                    stringsolution.setdefault(k, {})[header] = {"original": f"{val}"}
                    print("k", k)
                    if k not in stringrecommend:
                        stringrecommend[k] = {}
                    print("sb", stringrecommend)
                    stringrecommend[k][header] = {}
                    stringrecommend[k][header][
                        "solution"
                    ] = likeexact_instance_result_solution

                    print(stringrecommend)
                    if k not in check_fuzzy_string:
                        check_fuzzy_string[k] = {}
                    check_fuzzy_string[k][header] = False
                else:
                    stringsolution.setdefault(k, {})[header] = {"original": f"{val}"}
                    stringsolution[k][header][
                        "final"
                    ] = likeexact_instance_result_solution




def handle_fully_resolvable_string():
    
    global sql

    print(stringsolution)
    print("parse_result", parse_result)
    uuid_map = build_uuid_match_map(parse_result)
    print("uuid_map", uuid_map)

    
    for top_key, second_level in stringsolution.items():
        
        uuid = top_key.split("+", 1)[1] if "+" in top_key else None
        match = uuid_map.get(uuid, "未知 UUID")

        
        final_value = None
        for item in second_level.values():
            if isinstance(item, dict) and "final" in item:
                final_value = item["final"]
                break
        print("match", match)
        if(match == "Exact Matching"):
            print(type(final_value))
            print("final_value", final_value)
            final_value = ast.literal_eval(final_value)
            final_value = [f"'{x}'" for x in final_value]
            print("final_value",final_value)
            print("uuid",uuid)
            print(type(uuid))
            print({uuid: final_value})
            print(toolkit)
            
            sql = toolkit.substitute_where_equal_to_in_on_tree( tree,
            {uuid: final_value}
        )
            print("sql",sql)

        else:
            final_value = ast.literal_eval(final_value)
            final_value = [f"{x}" for x in final_value]
            sql = toolkit.substitute_where_like_to_or_on_tree(
    tree,           {uuid:final_value}
        )
    print(sql)


    return sql



def parse_sql_to_json(sql):
    global tree
    #tree = toolkit.parse(sql)
   # print("tree", tree)
    return  toolkit.parse_sql_to_json(tree)








def add_basic_interactive_features(spec):
    
    import copy
    new_spec = copy.deepcopy(spec)

    enc = new_spec.get("encoding") or {}
    new_spec["encoding"] = enc

    
    mark = new_spec.get("mark")
    mark_type = (mark.get("type") if isinstance(mark, dict) else mark)

    
    sel = new_spec.get("selection")
    if not isinstance(sel, dict):
        sel = {}
    new_spec["selection"] = sel

    
    def is_obj(d):
        return isinstance(d, dict)

    def get_field_from(ch_name):
        ch = enc.get(ch_name)
        return ch.get("field") if is_obj(ch) and "field" in ch else None

    def ensure_list(val):
        return val if isinstance(val, list) else [val]

    
    def build_tooltips_for_channels(channels):
        tips = []
        for ch in channels:
            ch_def = enc.get(ch)
            if not is_obj(ch_def):
                continue
            if "field" in ch_def:
                e = {"field": ch_def["field"], "type": ch_def.get("type", "quantitative")}
                if ch_def.get("bin"):
                    e["bin"] = True
                if "aggregate" in ch_def:
                    e["aggregate"] = ch_def["aggregate"]
                if "timeUnit" in ch_def:
                    e["timeUnit"] = ch_def["timeUnit"]
                tips.append(e)
        return tips

    
    if mark_type == "arc":
        cat_field = get_field_from("color") or get_field_from("detail") or get_field_from("theta")

        if cat_field:
            sel.setdefault("slice", {
                "type": "multi",
                "fields": [cat_field],
                "bind": "legend"
            })
            sel.setdefault("hover", {
                "type": "single",
                "fields": [cat_field],
                "on": "pointerover",
                "clear": "pointerout"
            })
        else:
            sel.setdefault("hover", {
                "type": "single",
                "on": "pointerover",
                "clear": "pointerout",
                "empty": "none"
            })

        if "opacity" not in enc:
            conditions = []
            if "hover" in sel:
                conditions.append({"param": "hover", "value": 1})
            if "slice" in sel:
                conditions.append({"param": "slice", "value": 1})
            if conditions:
                enc["opacity"] = {"condition": conditions, "value": 0.35}

        if "strokeWidth" not in enc and "hover" in sel:
            enc["strokeWidth"] = {"condition": {"param": "hover", "value": 2}, "value": 1}

        if not is_obj(mark):
            new_spec["mark"] = {"type": "arc", "stroke": "#fff"}
        else:
            mark.setdefault("stroke", "#fff")
            new_spec["mark"] = mark

        if "tooltip" not in enc:
            enc["tooltip"] = build_tooltips_for_channels(["theta", "color"])

        if "zoom" in sel:
            sel.pop("zoom", None)

    
    elif mark_type == "bar":
        x_field = get_field_from("x")  

        
        if "zoom" in sel:
            sel.pop("zoom", None)
        sel.setdefault("brushX", {
            "type": "interval",
            "encodings": ["x"],
            "translate": True,
            "zoom": True
        })

        
        if "hover" not in sel:
            if x_field:
                sel["hover"] = {
                    "type": "single",
                    "fields": [x_field],
                    "on": "pointerover",
                    "clear": "pointerout"
                }
            else:
                sel["hover"] = {"type": "single", "on": "pointerover", "clear": "pointerout", "empty": "none"}

        
        if "opacity" not in enc:
            enc["opacity"] = {
                "condition": {"param": "hover", "value": 1},
                "value": 0.5
            }

        
        if "tooltip" not in enc:
            enc["tooltip"] = build_tooltips_for_channels(["x", "y"])

        
        transforms = new_spec.get("transform")
        if not isinstance(transforms, list):
            transforms = []
        
        has_brush_filter = any(
            isinstance(t, dict) and isinstance(t.get("filter"), dict) and t["filter"].get("selection") == "brushX"
            for t in transforms
        )
        if not has_brush_filter:
            transforms.append({"filter": {"selection": "brushX"}})
        new_spec["transform"] = transforms

        
        if not is_obj(mark):
            new_spec["mark"] = {"type": "bar", "cursor": "pointer"}
        else:
            mark.setdefault("cursor", "pointer")
            new_spec["mark"] = mark

        
        x_enc = enc.get("x")
        if is_obj(x_enc) and x_enc.get("type") == "nominal":
            axis = x_enc.get("axis") or {}
            axis.setdefault("labelAngle", 0)
            x_enc["axis"] = axis
            enc["x"] = x_enc

    
    else:
        sel.setdefault("zoom", {"type": "interval", "bind": "scales"})
        sel.setdefault("hover", {"type": "single", "on": "mouseover", "empty": "none"})
        if "tooltip" not in enc:
            enc["tooltip"] = build_tooltips_for_channels(["x", "y"])

        x_enc = enc.get("x")
        if is_obj(x_enc) and x_enc.get("type") == "nominal":
            axis = x_enc.get("axis") or {}
            axis["labelAngle"] = -45
            x_enc["axis"] = axis
            enc["x"] = x_enc

    new_spec["encoding"] = enc
    new_spec["selection"] = sel
    return new_spec




@app.route("/upload", methods=["POST"])
def upload_file():
    global df, file_name, column_names, unit, description

    uploaded_file = request.files["csv_file"]
    file_name = request.form.get("file_name", "").replace("-", "_")

    print("Uploaded file:", uploaded_file)
    print("File name:", file_name)
    df = pd.read_csv(uploaded_file)


    df.columns = [col.replace(" ", "_") for col in df.columns]

    print("Data preview:")
    print(df.head(3))

    analyzer = DataAnalyzer(sample_size=50)
    description = analyzer.analyze_dataframe_in_english(df)
    print("Data description:", description)

    
    response = jsonify(
        {"message": "File uploaded successfully", "description": description}
    )

    
    threading.Thread(target=process_embeddings, args=(df,)).start()

    return response


@app.route("/gettext", methods=["POST"])
def submit():
    
    global df, file_name, goal, sql, description,tree,toolkit,parse_result

    data = request.get_json()
    reset_globals()
    goal = data.get("text")
    print(f"Received text: {goal}")
    print("Data preview:", df.head(3))
    now = datetime.now()
    print(now.strftime("%H:%M:%S"))



    Ambigioussql_instance = Ambigioussql(df, file_name)
    print("Ambigioussql_instance:")
    Ambigioussql_instance_result = Ambigioussql_instance.Generatsql(text=goal)
    sql = Ambigioussql_instance_result
    print("Generated SQL:", sql)

    toolkit = BraceSQLToolkit()

    tree = toolkit.parse(sql)

    while True:
        try:
            tree, placeholder_infos = validate_sql_strict(sql)
            print("占位符信息 =", placeholder_infos)
            if len(placeholder_infos) == 0:
                print("SQL 中没有占位符，说明没有模糊概念")
                parse_result = parse_sql_to_json(sql=sql)
                if parse_result.get("type") == False:
                    print("既没有文本概念也没有字符串模糊概念")
                    Translate_instance_result = build_translation_sentence(
                        original_question=goal,
                        sql_query=sql,
                        tree=tree,
                    )
                    print(Translate_instance_result)
                    return jsonify(
                        {
                            "textfuzzy": False,
                            "stringfuzzy": False,
                            "vis": None,
                            "stringresult": None,
                            "textrecommend": None,
                            "finalquestion": Translate_instance_result["translated_question"],
                            "original_question": goal,
                            "initial_fuzzy_recommendations": Translate_instance_result[
                                "initial_fuzzy_recommendations"
                            ],
                            "awaitingFollowup": True,
                        }
                    )

                else:
                    process_fuzzy_string(parse_result)
                    print(stringrecommend)
                    if len(stringrecommend) == 0:
                        Translate_instance_result = build_translation_sentence(
                            original_question=goal,
                            sql_query=sql,
                             tree=tree,
                        )
                        return jsonify(
                            {
                                "textfuzzy": False,
                                "stringfuzzy": False,
                                "vis": None,
                                "stringresult": None,
                                "textrecommend": None,
                                "finalquestion": Translate_instance_result["translated_question"],
                                "original_question": goal,
                                "initial_fuzzy_recommendations": Translate_instance_result[
                                    "initial_fuzzy_recommendations"
                                ],
                                "awaitingFollowup": True,
                            }
                        )
                    else:

                        return jsonify(
                            {
                                "textfuzzy": False,
                                "stringfuzzy": True,
                                "stringresult": stringrecommend,
                                "textrecommend": None,
                                "vis": None,
                            }
                        )


            else:
                for info in placeholder_infos:
                    print(info)
                    if info['allowed_context']=='Select' and info['direct_parent']=='Select':
                        print(info['inner_sql'])
                        s=info['inner_sql']
                        while True:
                            add_info_instance = Colfuzzy(df, file_name)
                            add_info_result = add_info_instance.Generation(
                                fuzzy=s, unit=unit, question=goal, sql=sql
                            )
                            parsed_result = json.loads(add_info_result)
                            print("Parsed result:", parsed_result)
                            if all(item in df.columns for item in parsed_result):
                                break  
                        if len(parsed_result) == 1: 
                            sql = toolkit.substitute_select_placeholders_on_tree(
                                tree, {info['uuid']: parsed_result}
                            )
                            print(type(info['uuid']))
                            print("Updated SQL:", sql)
                        else:              
                            textrecommend[s+'+'+'SELECT'+'+'+info['uuid']] = {
                                    "category": "multiple_column",
                                    "solution": parsed_result,
                                }
                            check_fuzzy_text[s+'+'+'SELECT'+'+'+info['uuid']] = False
                            print(textrecommend[s+'+'+'SELECT'+'+'+info['uuid']])   

                    elif info['allowed_context']=='WhereComparison':
                        print(info['inner_sql'])
                        range_recommendation = {}
                        range_recommendation['Summary']=column_summary(df, info['where_left_col'])
                        range_recommendation['Recommend']=f"{info['inner_sql']} is related from {info['where_left_col']}, should be defined from {df[info['where_left_col']].min()} to {df[info['where_left_col']].max()}"
                        textrecommend[info['inner_sql']+'+'+'where1'+'+'+info['uuid']] = {
                        "category": "no_scientific_basis",
                        "solution": range_recommendation,
                    }
                        check_fuzzy_text[info['inner_sql']+'+'+'where1'+'+'+info['uuid']] = False
            break
        except (ParseError, DisallowedNodeError) as e:
            print("SQL 语法/校验错误：", e)
            ReGeneratsql_instance = ReGeneratsql(df, file_name)
            sql = ReGeneratsql_instance.Generate(
                text=goal, syntax_error=e
            )

    print(textrecommend)
    if len(textrecommend) != 0:
        return jsonify(
            {
                "textrecommend": textrecommend,
                "textfuzzy": True,
                "stringfuzzy": False,
                "stringresult": None,
                "vis": None,
            }
        )
    else:
    
                print("SQL 中没有占位符，说明没有模糊概念")
                parse_result = parse_sql_to_json(sql=sql)
                if parse_result.get("type") == False:
                    print("既没有文本概念也没有字符串模糊概念")
                    Translate_instance_result = build_translation_sentence(
                        original_question=goal,
                        sql_query=sql,
                         tree=tree,
                    )
                    print(Translate_instance_result)
                    return jsonify(
                        {
                            "textfuzzy": False,
                            "stringfuzzy": False,
                            "vis": None,
                            "stringresult": None,
                            "textrecommend": None,
                            "finalquestion": Translate_instance_result["translated_question"],
                            "original_question": goal,
                            "initial_fuzzy_recommendations": Translate_instance_result[
                                "initial_fuzzy_recommendations"
                            ],
                            "awaitingFollowup": True,
                        }
                    )

                else:
                    process_fuzzy_string(parse_result)
                    print(stringrecommend)
                    if len(stringrecommend) == 0:
                        Translate_instance_result = build_translation_sentence(
                            original_question=goal,
                            sql_query=sql,
                             tree=tree,
                        )
                        return jsonify(
                            {
                                "textfuzzy": False,
                                "stringfuzzy": False,
                                "vis": None,
                                "stringresult": None,
                                "textrecommend": None,
                                "finalquestion": Translate_instance_result["translated_question"],
                                "original_question": goal,
                                "initial_fuzzy_recommendations": Translate_instance_result[
                                    "initial_fuzzy_recommendations"
                                ],
                                "awaitingFollowup": True,
                            }
                        )
                    else:

                        return jsonify(
                            {
                                "textfuzzy": False,
                                "stringfuzzy": True,
                                "stringresult": stringrecommend,
                                "textrecommend": None,
                                "vis": None,
                            }
                        )   
    
@app.route("/api/fuzzytext", methods=["POST"])
def fuzzytext():
    
    global sql, goal
    data = request.get_json()
    category = data.get("category")
    solution = data.get("userInput")
    key = data.get("keyName")
    print("Received fuzzytext submission:")
    print("Category:", category, "Key:", key, "Solution:", solution)

    
    if re.match(r"^\[\s*.*\s*\]$", solution) or category=='no_scientific_basis':
        check_fuzzy_text[key] = True
        if re.match(r"^\[\s*.*\s*\]$", solution):
             solution = json.loads(solution)
        
        textsolution[key] =solution
        if all(check_fuzzy_text.values()):
            synthesized_sql, parse_result = handle_fully_resolvable_text()
            sql = synthesized_sql
            print("Waiting for embeddings to be processed...")
            embedding_event.wait()
            if parse_result.get("type") == True:
                process_fuzzy_string(parse_result)
                all_true = all(
                    value
                    for sub_dict in check_fuzzy_string.values()
                    for value in (
                        sub_dict.values() if isinstance(sub_dict, dict) else [sub_dict]
                    )
                )
                if all_true:
                    Translate_instance_result = build_translation_sentence(
                        original_question=goal,
                        sql_query=sql,
                         tree=tree,
                    )
                    print(Translate_instance_result)
                    return (
                        jsonify(
                            {
                                "message": "Data received",
                                "category": category,
                                "key": key,
                                "fuzzyresult": {"level": "fully_resolvable"},
                                "vis": None,
                                "stringresult": None,
                                "finalquestion": Translate_instance_result["translated_question"],
                                "original_question": goal,
                                "initial_fuzzy_recommendations": Translate_instance_result[
                                    "initial_fuzzy_recommendations"
                                ],
                                "awaitingFollowup": True,
                            }
                        ),
                        200,
                    )
                else:
                    return (
                        jsonify(
                            {
                                "message": "Data received",
                                "category": category,
                                "key": key,
                                "fuzzyresult": {"level": "fully_resolvable"},
                                "vis": None,
                                "stringresult": stringrecommend,
                            }
                        ),
                        200,
                    )
            else:
                Translate_instance_result = build_translation_sentence(
                    original_question=goal,
                    sql_query=sql,
                     tree=tree,
                )
                print(Translate_instance_result)
                return (
                    jsonify(
                        {
                            "message": "Data received",
                            "category": category,
                            "key": key,
                            "fuzzyresult": {"level": "fully_resolvable"},
                            "vis": None,
                            "stringresult": None,
                            "finalquestion": Translate_instance_result["translated_question"],
                            "original_question": goal,
                            "initial_fuzzy_recommendations": Translate_instance_result[
                                "initial_fuzzy_recommendations"
                            ],
                            "awaitingFollowup": True,
                        }
                    ),
                    200,
                )
        return (
            jsonify(
                {
                    "message": "Data received",
                    "category": category,
                    "key": key,
                    "fuzzyresult": {"level": "fully_resolvable"},
                    "stringresult": None,
                    "vis": None,
                }
            ),
            200,
        )

    text_content_instance = TextContent(df, file_name)
    text_content_result = text_content_instance.Check(
        question=goal, sql=sql, unit=unit, key=key.split('+')[0], solution=solution
    ) 
    print('solution',solution)
    
    if "/" in solution:
        parts = solution.split("/")
        print(parts)
        after_parts = parts[1:]
        for part in after_parts:
            print(part)
            if part not in df.columns:
                text_content_result["level"] ="completely_unresolvable"
                break
            if (df[part] == 0).any():
                text_content_result["level"] ="completely_unresolvable"
                break
    if text_content_result["level"] == "fully_resolvable":
        check_fuzzy_text[key] = True
        expr =solution


        
        if " as " in expr.strip().lower():
            result22 = expr.strip()
        else:
            result22 = f"({expr.strip()}) AS {key.split('+')[0]}"

        print(result22)
        
        textsolution[key] = [result22]
        if all(check_fuzzy_text.values()):
            synthesized_sql, parse_result = handle_fully_resolvable_text()
            sql = synthesized_sql
            print("Waiting for embeddings to be processed...")
            embedding_event.wait()
            if parse_result.get("type") == True:
                process_fuzzy_string(parse_result)
                all_true = all(
                    value
                    for sub_dict in check_fuzzy_string.values()
                    for value in (
                        sub_dict.values() if isinstance(sub_dict, dict) else [sub_dict]
                    )
                )
                if all_true:
                    Translate_instance_result = build_translation_sentence(
                        original_question=goal,
                        sql_query=sql,
                         tree=tree,
                    )
                    print(Translate_instance_result)
                    return (
                        jsonify(
                            {
                                "message": "Data received",
                                "category": category,
                                "key": key,
                                "fuzzyresult": text_content_result,
                                "vis": None,
                                "stringresult": None,
                                "finalquestion": Translate_instance_result["translated_question"],
                                "original_question": goal,
                                "initial_fuzzy_recommendations": Translate_instance_result[
                                    "initial_fuzzy_recommendations"
                                ],
                                "awaitingFollowup": True,
                            }
                        ),
                        200,
                    )
                else:
                    return (
                        jsonify(
                            {
                                "message": "Data received",
                                "category": category,
                                "key": key,
                                "fuzzyresult": text_content_result,
                                "vis": None,
                                "stringresult": stringrecommend,
                            }
                        ),
                        200,
                    )
            else:
                Translate_instance_result = build_translation_sentence(
                    original_question=goal,
                    sql_query=sql,
                     tree=tree,
                )
                print(Translate_instance_result)
                return (
                    jsonify(
                        {
                            "message": "Data received",
                            "category": category,
                            "key": key,
                            "fuzzyresult": text_content_result,
                            "vis": None,
                            "stringresult": None,
                            "finalquestion": Translate_instance_result["translated_question"],
                            "original_question": goal,
                            "initial_fuzzy_recommendations": Translate_instance_result[
                                "initial_fuzzy_recommendations"
                            ],
                            "awaitingFollowup": True,
                        }
                    ),
                    200,
                )
        return (
            jsonify(
                {
                    "message": "Data received",
                    "category": category,
                    "key": key,
                    "fuzzyresult": text_content_result,
                    "stringresult": None,
                    "vis": None,
                }
            ),
            200,
        )
    elif text_content_result["level"] in [
        "partially_resolvable",
        "completely_unresolvable",
    ]:
        return (
            jsonify(
                {
                    "message": "Data received",
                    "category": category,
                    "key": key,
                    "fuzzyresult": text_content_result,
                    "stringresult": None,
                    "vis": None,
                }
            ),
            200,
        )


@app.route("/api/fuzzystring", methods=["POST"])
def fuzzystring():
    
    global sql, goal,tree
    data = request.get_json()
    columnname = data.get("columnname")
    key = data.get("backendKey")
    solution = data.get("userInput")

    print(check_fuzzy_string)
    check_fuzzy_string[key][columnname] = True

    
    if key in stringsolution and columnname in stringsolution[key]:
        stringsolution[key][columnname]["final"] = solution
    print("Fuzzystring received:", data)
    all_true = all(
        value
        for sub_dict in check_fuzzy_string.values()
        for value in (sub_dict.values() if isinstance(sub_dict, dict) else [sub_dict])
    )

    if all_true:
        orginalquestion=goal

        synthesized_sql = handle_fully_resolvable_string()
        print('sql',synthesized_sql)
        print('goal',goal)
        Translate_instance_result = build_translation_sentence(
            original_question=orginalquestion,
            sql_query=synthesized_sql,
             tree=tree,
        )
        print(Translate_instance_result)
        return jsonify(
            {
                "message": "Data received",
                "vis": None,
                "finalquestion": Translate_instance_result["translated_question"],
                "original_question": goal,
                "initial_fuzzy_recommendations": Translate_instance_result[
                    "initial_fuzzy_recommendations"
                ],
                "awaitingFollowup": True,
            }
        ), 200

    return jsonify({"message": "Data received", "vis": None}), 200


@app.route("/api/runfollowups", methods=["POST"])
def run_followups():
    
    global goal, sql
    final_uuid_result = request.get_json(silent=True) or []
    final_tree=apply_final_uuid_result(
        final_uuid_result=final_uuid_result,
        tree=tree,
        textrecommend=textrecommend,
        string_recommend=stringrecommend,
        string_recommend_type=build_uuid_match_map(parse_result)
        if isinstance(parse_result, dict)
        else {},
    )
    print("Received runfollowups request with data:", final_uuid_result)    

    if sql is None or not goal:
        return jsonify({"message": "No pending query to continue.", "vis": None}), 400

    vis_result = generate_visual_recommendations(question=goal, sql_query=final_tree.sql())
    reset_globals()
    return jsonify({"message": "Data received", "vis": vis_result}), 200


@app.route("/api/changechart", methods=["POST"])
def changechart():
    data = request.get_json()

    chartquery = data.get("chartParam")
    vegalite = data.get("vegaliteSpec")
    changechartkey=data.get("key")
    print(changechartkey)
    print(type(vegalite))
    print(chartquery)
    print(vegalite)

    new_config = copy.deepcopy(vegalite)

    new_config["data"]["values"] = new_config["data"]["values"][:3]

    
    changechart = Changechart()
    modified_spec = changechart.Generate(request=chartquery, vegalite=new_config)
    print(modified_spec)
    modified_spec["data"]["values"] = vegalite["data"]["values"]

    return jsonify({"message": "Data received", "chart": add_basic_interactive_features(modified_spec),"key":changechartkey}), 200


@app.route("/api/changeinsight", methods=["POST"])
def changeinsight():
    global goal
    global file_name
    global allvisresult

    data = request.get_json()
    keys = list(data.keys())
    print(keys)
    key = data.get("key")
    steps = data.get("steps")
    print(data)
    print(allvisresult)
    print(list(allvisresult[key].keys()))

    all_but_last = steps[:-1]
    last_step = steps[-1]
    
    last_key = last_step.get("key")
    data_values = allvisresult[key]["result_df"]

    data_values_df = pd.DataFrame(data_values)
    now = datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M:%S"))

    changeinsight_instance = ChangeInsight5(df=data_values_df, file_name=file_name)
    changeinsight_instance_result = changeinsight_instance.newstory(
        all_but_last=all_but_last,
        last_key=last_key,
        question=goal,
        vegalite_spec=allvisresult[key]["VisualRecommend_instance_result"],
    )
    while changeinsight_instance_result is None:
        changeinsight_instance_result = changeinsight_instance.newstory(
        all_but_last=all_but_last,
        last_key=last_key,
        question=goal,
        vegalite_spec=allvisresult[key]["VisualRecommend_instance_result"],
    )
    now = datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M:%S"))
    if "vegalite" in changeinsight_instance_result:
        vegalite_content = changeinsight_instance_result.pop("vegalite")

        vegalite_content["data"] = {}
        vegalite_content["data"]["values"] = data_values_df.to_dict(orient="records")

        changeinsight_instance_result = [
            {"key": k, "value": v} for k, v in changeinsight_instance_result.items()
        ]

        print(changeinsight_instance_result)
        vegalite_content = add_basic_interactive_features(vegalite_content)
        allvisresult[key]["VisualRecommend_instance_result"] = vegalite_content
        print(vegalite_content)

        return (
            jsonify(
                {
                    "message": "Data received",
                    "changeinsight": changeinsight_instance_result,
                    "vegalite": vegalite_content,
                }
            ),
            200,
        )
    else:
        changeinsight_instance_result = [
        {"key": k, "value": v} for k, v in changeinsight_instance_result.items()
    ]
        return (
            jsonify(
                {
                    "message": "Data received",
                    "changeinsight": changeinsight_instance_result,
                    "vegalite": None,
                }
            ),
            200,
        )



if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
