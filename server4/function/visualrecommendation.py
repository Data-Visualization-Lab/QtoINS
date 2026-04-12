from openai import OpenAI
import json
import pandas as pd
from collections import OrderedDict

from features.single_field_features import extract_single_field_features
from features.pairwise_field_features import extract_pairwise_field_features
from features.aggregate_single_field_features import extract_aggregate_single_field_features
from features.aggregate_pairwise_field_features import extract_aggregate_pairwise_field_features

prompt="""
You have a table where the user has selected certain columns. 
You are provided with:
1) Up to the first three rows from the user-selected columns (or all rows if there are fewer than three). These rows are provided due to context window limitations.
2) The feature information for all selected columns (e.g., column data types such as categorical or numerical, total column count, percentage of categorical columns, mean correlation between pairs of quantitative columns, etc.).
3) The user's question regarding how to visualize or analyze these columns.

Your task is to:
- Use only the provided rows when constructing any Vega-Lite data references (because of context window constraints).
- Take advantage of the provided feature information (e.g., which columns are categorical or numeric) to determine the most suitable chart type and encoding.
- Combine the user’s question with the feature information to produce the best possible Vega-Lite chart for those three (or fewer) rows of data.

Important:
- You must only return the Vega-Lite JSON specification that best visualizes the provided data in response to the user's question.
- Do not include data beyond the provided rows.
- The chart’s design should reflect both the user’s intent and the given feature information.

You should focus on how data is embedded into the Vega-Lite chart according to the user’s intent and the given feature information.

I only provide you with the first 3 rows of the table to help you better understand the specific data content and to generate a Vega-Lite chart that conforms to the Vega-Lite syntax.
You must focus on the user's intent and the feature information of the selected data to create the best possible Vega-Lite chart.

"""





def extract_features_from_fields(fields, compute_features_config, fid=None):
    """
    你的特征提取函数实现，与之前相同。
    fields: 形如 [ (col_name, {'uid': ..., 'order': ..., 'data': ...}), (...), ... ]
    fid: 一个字符串，用来标识这个数据集或表格。
    """
    results = {}
    MAX_FIELDS = len(fields)

    df_feature_tuples = OrderedDict({'fid': fid})
    df_feature_tuples_if_exists = OrderedDict({'fid': fid})

    # 1. 单字段特征 & 解析
    single_field_features, parsed_fields = ([], [])
    if compute_features_config['single_field'] or compute_features_config['field_level_features']:
        single_field_features, parsed_fields = extract_single_field_features(
            fields,
            fid,
            MAX_FIELDS=MAX_FIELDS
        )
        for i, field_features in enumerate(single_field_features):
            if not field_features.get('exists'):
                continue
            field_num = i + 1
            for field_feature_name, field_feature_value in field_features.items():
                if field_feature_name not in ['fid', 'field_id', 'exists']:
                    field_feature_name_with_num = f"{field_feature_name}_{field_num}"
                    df_feature_tuples_if_exists[field_feature_name_with_num] = field_feature_value
        
        results['single_field_features'] = single_field_features

    # 2. 聚合单字段特征
    if compute_features_config['aggregate_single_field']:
        aggregate_single_field_features = extract_aggregate_single_field_features(
            single_field_features
        )
        for k, v in aggregate_single_field_features.items():
            df_feature_tuples[k] = v
            df_feature_tuples_if_exists[k] = v
        results['aggregate_single_field_features'] = aggregate_single_field_features

    # 3. 两两字段特征
    pairwise_field_features_result = []
    if compute_features_config['pairwise_field'] or compute_features_config['aggregate_pairwise_field']:
        pairwise_field_features_result = extract_pairwise_field_features(
            parsed_fields,
            single_field_features,
            fid,
            MAX_FIELDS=MAX_FIELDS
        )
        results['pairwise_field_features'] = pairwise_field_features_result

    # 4. 聚合两两字段特征
    if compute_features_config['aggregate_pairwise_field']:
        aggregate_pairwise_field_features = extract_aggregate_pairwise_field_features(
            pairwise_field_features_result
        )
        for k, v in aggregate_pairwise_field_features.items():
            df_feature_tuples[k] = v
            df_feature_tuples_if_exists[k] = v
        results['aggregate_pairwise_field_features'] = aggregate_pairwise_field_features

    results['df_feature_tuples'] = df_feature_tuples
    results['df_feature_tuples_if_exists'] = df_feature_tuples_if_exists
    return results

def run_feature_extraction_for_one_df(df, fid="my_data"):

    """
    输入单个 DataFrame，进行特征提取并返回提取的各类特征。
    fid: 一个字符串，用来标识这个数据集或表格（可自定义）。
    """
    
    # 1. 将 df 的每一列组装成 fields
    compute_features_config = {
            'single_field': True,
            'aggregate_single_field': True,
            'pairwise_field': True,
            'aggregate_pairwise_field': True,
            'field_level_features': False,
            'chart_outcomes': False,
            'field_outcomes': False,
            'supplement': False,
        }
    fields = []
    for col_name in df.columns:
        col_data = df[col_name].tolist()
        field_info = {
            'uid': col_name,
            'order': col_name,
            'data': col_data
        }
        fields.append((col_name, field_info))

    # 2. 调用特征提取函数（extract_features_from_fields）
    extraction_results = extract_features_from_fields(
        fields=fields,
        compute_features_config=compute_features_config,
        fid=fid
    )
    
    # 3. 取出各类特征
    single_field_features = extraction_results.get('single_field_features', [])
    pairwise_field_features = extraction_results.get('pairwise_field_features', [])
    aggregated_single_field_features = extraction_results.get('aggregate_single_field_features', {})
    aggregated_pairwise_field_features = extraction_results.get('aggregate_pairwise_field_features', {})

    # 4. 将它们组织成 final_features 返回
    final_features = {
        "single_field_features": single_field_features,
        "pairwise_field_features": pairwise_field_features,
        "aggregated_single_field_features": aggregated_single_field_features,
        "aggregated_pairwise_field_features": aggregated_pairwise_field_features
    }

    return final_features

def df_to_text(df):
    """
    将任何 DataFrame 转换成多行文本。
    每一行形如：
      col1: value1, col2: value2, col3: value3 ...
    """
    lines = []
    for _, row in df.iterrows():
        # 收集本行所有 "列名: 值"
        line_parts = []
        for col in df.columns:
            line_parts.append(f"{col}: {row[col]}")
        # 将这些部件用 ", " 拼接在一起
        line_str = ", ".join(line_parts)
        lines.append(line_str)
    
    # 多行字符串，用换行符拼接
    return "\n".join(lines)

class VisualRecommend:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    def Recommend(self, question):
        df_first_three = self._df[:3]

# 调用函数得到字符串
        result_str = df_to_text(df_first_three)

        p1 = "User question is: " + question+"\n"
        p2 = "Table's first 3 rows =>"+ " \n"+result_str+" \n"
        final_features = run_feature_extraction_for_one_df(self._df, fid="my_data")
        single_agg = final_features.get("aggregated_single_field_features", {})
        pairwise_agg = final_features.get("aggregated_pairwise_field_features", {})
        combined = {}
        combined.update(single_agg)
        combined.update(pairwise_agg)
        lines = []
        for sub_k, sub_v in combined.items():
            # 将键、值组合成字符串
            line = f"{sub_k}: {sub_v}"
            lines.append(line)
        
        # 把所有字段拼成多行文本
        multiline_str = "\n".join(lines)
        print(len(lines))
        p3="Feature information =>"+ " \n"+multiline_str+" \n"
        promptt = p1 +p2+p3
   
       
       

        api_key="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"
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
        model="ft:gpt-4o-2024-08-06:personal:vr:AsLlaX24",
        messages=[
            {
            "role": "system",
           "content": [
                {
                "type": "text",
                "text": prompt
                }
                     ]
            },
            {
            "role": "user",
            "content":[
                        {
                        "type": "text",
                        "text": promptt
                        }
                    ]
            }
        ],
          temperature=0,
          max_tokens=4096,
          top_p=1
        )

        vr=response.choices[0].message.content
      
        vr = json.loads(vr)

        # 将 DataFrame 转换成列表+字典 格式
        df_records = self._df.to_dict(orient='records')

        # 替换 vr["data"]["values"] 的值
        vr["data"]["values"] = df_records


      
        return   vr