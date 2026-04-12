from openai import OpenAI
import json

import pandas as pd

prompt="""
You are now a knowledgeable expert. I will provide a table and its columns; please use this information to answer my questions. In my case, some parts of my SQL are different. The fuzzy concepts in my SQL are enclosed in {}. Vague concepts now fall into in this scenarios:


When the vague concept in the query is unclear due to multiple possible matches with the table columns and there are at least two possible columns that could match, you must return a Python list containing all potential column names the vague concept might correspond to. Only return this list, without additional information or explanation.

Examples:

Example for Scenario 1:
My table name is movies.
The columns in my table are: title, director, genre, 'avg rating', 'max rating', 'min rating'
My question is: show me the relationship between rating and title;
My SQL is: SELECT {rating}, title FROM movies;
You must return:
["avg rating", "max rating", "min rating"]

"""
def clean_string(input_string):
    # 移除开头和结尾的反引号
    input_string = input_string.strip('`')
    # 如果移除反引号后，字符串开头是 json，移除它
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  # 移除开头的 json 并去掉多余的空格
    return input_string.strip()  # 再次清理两边空格
class Colfuzzy:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    def Generation(self,fuzzy,unit,question,sql):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        unit_str=", ".join(str(item) for item in unit)
 


        p1 = "My table name is  " + self.file_name+" \n"
        p2 = "The columns in my table are: "+column_names_str+" \n"
        p3="The units of the columns in this table are as follows: "+unit_str+" \n"
        p4="My question is: "+question+" \n"
        p5="My sql is: "+sql+" \n"
        p6="In my case, some parts of my SQL are different. The fuzzy concepts in my SQL are enclosed in {}\n"
        p7="In this task, you only need to address only one vague concept: "+fuzzy+" \n"
        p8 = "My first three rows of data are:\n"
        p8 += " | ".join(self._df.columns) + "\n"  # 添加列名
        p8 += "\n".join(self._df.head(3).astype(str).apply(lambda row: " | ".join(row), axis=1))  # 添加行数据
       
       
        promptt = p1+p2+p4+p5+p6+p7+p8
        print(promptt)

        api_key="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"
        client = OpenAI(api_key=api_key)
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
        temperature=1,
        max_tokens=4096,
        top_p=1
        )
        addition_information=response.choices[0].message.content
        addition_information= clean_string(addition_information)

        return addition_information