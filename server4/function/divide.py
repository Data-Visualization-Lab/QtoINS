from openai import OpenAI
import json

import pandas as pd
prompt="""Task: Generate a clear and precise question along with a brief description to facilitate data visualization.

Instructions:

Task Overview:

Produce one exact and precise question.

Column Restrictions:

Use only columns present in the original SQL statement; do not introduce new columns.

Visualization Requirement:

Ensure the question corresponds directly with available columns to facilitate meaningful visual representation.

Intent Preservation:

Preserve the original intent and meaning of the user's query.

Correspondence:

Provide a brief description summarizing the semantic meaning of the question.

The question must exactly correspond to the original data intent.

Output Format:

The output should be a JSON object containing:

"description": A brief summary of the semantic meaning.

"question": An exact and precise question suitable for visualization.

Example:

Table Name: "olympic_medals"

Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'

Original Question: Analyze the total number of medals by year.

Expected Output:
{
"description": "the total number of gold and silver medals by year",
"question": "Analyze the total number of gold and silver medals by year."
}

Remember:

Only use columns from the original statement.

Preserve the user's original intent clearly.

The question must precisely correspond with available columns."""




def clean_string(input_string):
    # 移除开头和结尾的反引号
    input_string = input_string.strip('`')
    # 如果移除反引号后，字符串开头是 json，移除它
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  # 移除开头的 json 并去掉多余的空格
    return input_string.strip()  # 再次清理两边空格

class Divide:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    def Generate(self, question,sql,unit):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        unit_str=", ".join(str(item) for item in unit)

        p1 = "My table name is  " + self.file_name+" .\n"
        p2 = "The columns in my table are: "+column_names_str+" .\n"
        p3="The units of the columns in this table are as follows: "+unit_str+" .\n"
        p4="My origianl question is: "+question+" .\n"
        p5="My original sql is: "+sql+" .\n"
        
        p6="""
        You must strictly use only columns already selected in the original SQL statement. Do not introduce any new columns.
    Please return only the specific content in JSON format without any additional information, not even the word JSON.
      """
       
        promptt = p1 +p2+p3+p4+p5+p6
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
          temperature=0,
          max_tokens=2048,
          top_p=1
        )
        content=response.choices[0].message.content
        print(content)
        content = clean_string(content)
        content = json.loads(content)
      
        return content