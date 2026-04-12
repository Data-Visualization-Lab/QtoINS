from openai import OpenAI
import json

import pandas as pd

prompt = """

You are an expert in SQL and creative problem-solving. We have an SQL syntax where ambiguous concepts are enclosed in curly braces {}. You will receive:
    • A table schema.
    • An SQL query containing an ambiguous concept (enclosed in {}).
    • A proposed textual solution to clarify the ambiguity.

Your task is to categorize whether the provided textual solution logically and completely resolves the ambiguity using ONLY the information available from the given table schema.

Important rules:
- The provided solution must directly and exactly replace the ambiguous concept in the SQL query.
- The replacement must match exactly in spelling, spacing, punctuation, underscores, and capitalization as shown in the schema and original SQL.
- Even the smallest mismatch (missing/extra underscores, wrong case, wrong spacing, punctuation differences, etc.) makes the solution incorrect.

Categorize the resolution into exactly one of these two levels:
    1. "fully_resolvable":
       The textual solution entirely resolves the ambiguity by clearly using columns and expressions provided explicitly in the table schema. The solution, when directly replacing the ambiguous concept, produces a ready-to-execute SQL query.
    2. "completely_unresolvable":
       The textual solution references concepts or data not included in or calculable from the given table schema, or does not exactly match the column names or expressions required by the schema.

Return ONLY in this JSON format without any additional commentary or explanation:

{
  "level": "",
}

Example 1 (fully_resolvable):
Table: "product_sales"
Columns: "product_id", "product_name", "category", "price", "units_sold", "revenue"
SQL: SELECT product_name, {best_selling} as top_products FROM product_sales ORDER BY {best_selling} DESC LIMIT 5;
Solution: "price * units_sold"
Expected JSON response:
{
  "level": "fully_resolvable",
}

Example 2 (completely_unresolvable):
Table: "store_inventory"
Columns: "store_id", "product_id", "quantity", "price"
SQL: SELECT store_id, {most_valuable} FROM store_inventory GROUP BY store_id ORDER BY {most_valuable} DESC;
Solution: "The most valuable stores are the ones located in high-income zip codes."
Expected JSON response:
{
  "level": "completely_unresolvable",
}

Example 3 (completely_unresolvable):
Table: "orders"
Columns: "order_id", "customer_id", "order_date", "total_amount", "discount_rate"
SQL: SELECT customer_id, {final_price} as discounted_total FROM orders;
Solution: "total amount * (1 - discount rate)"
Reason: Column names in the schema are "total_amount" and "discount_rate". The provided solution uses spaces instead of underscores, so it does not exactly match the schema column names.
Expected JSON response:
{
  "level": "completely_unresolvable",
}
"""

def clean_string(input_string):
    # 移除开头和结尾的反引号
    input_string = input_string.strip('`')
    # 如果移除反引号后，字符串开头是 json，移除它
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  # 移除开头的 json 并去掉多余的空格
    return input_string.strip()  # 再次清理两边空格

class TextContent:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    def Check(self, question,sql,unit,key,solution):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        unit_str=", ".join(str(item) for item in unit)


        p1 = "My table name is " + self.file_name+" \n"
        p2 = "The columns in my table are: "+column_names_str+" \n"
        p3="The units of the columns in this table are as follows: "+unit_str+" \n"
        p4="My question is: "+question+" \n"
        p5="My sql is: "+sql+" \n"
        p6="In this task, The fuzzy concept you need to solve is "+key+"\n The solution is: "+ solution+" \n"
        p7 = "My first three rows of data are:\n"
        p7 += " | ".join(self._df.columns) + "\n"  # 添加列名
        p7 += "\n".join(self._df.head(5).astype(str).apply(lambda row: " | ".join(row), axis=1))  # 添加行数据


        
        promptt = p1 +p2+p4+p5+p6+p7


        api_key="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"
        client = OpenAI(api_key=api_key)
        print(promptt)
        response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
            "role": "system",
            "content": prompt
            },
            {
            "role": "user",
            "content":promptt
            }
        ],
        temperature=0,
        max_tokens=512,
        top_p=1
        )
        content=response.choices[0].message.content
        content=clean_string(content)
        print(content)
        content=json.loads(content)

        return content