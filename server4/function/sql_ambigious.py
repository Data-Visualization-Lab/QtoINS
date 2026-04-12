from openai import OpenAI
prompt = """
Your task is to generate an 'SQL' statement strictly adhering to DuckDB syntax based on the user’s question. 
Whenever a concept in the user’s request is ambiguous, you must encapsulate all ambiguous concept strictly and directly within curly braces {} without attempting to infer or clarify the user’s intent.
STRICT POSITION RULES FOR {}
- The {} placeholder is ONLY allowed in the following three cases but could appear multiple times:
  1. In the SELECT clause, replacing the name of a non-aggregated column or  inside aggregate function (e.g., SUM, MAX, MIN, COUNT,AVG) arguments (e.g., SUM({value}) is correct).
  2. A placeholder in the WHERE clause may be used only when replacing a literal value that is explicitly paired with a specific numeric column. It must appear on the right-hand side of the comparison, and the comparison operator must be one of {>, >=, <, <=}; the ‘=’ operator is not allowed.
  3.A placeholder in the limit clause and in the GROUP BY clause.

- Example
  - Table Name: "olympic_medals"
  - Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'
  - User's question: “Compare the medals for football by country.”  
  - Generated SQL:  
    SELECT Country, {medal} FROM olympic_medals WHERE Sport = 'Football';
  -reason:'medal' is ambiguous, medal can be Bronze Medal, Gold Medal, Silver Medal, Total Medal
- Example 

  - Table Name: "olympic_medals"
  - Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'
  - User's question: “Identify the top 3 older sports with the highest number of athletes after 2016.”  
  - Generated SQL:  

    SELECT Sport, COUNT(*) AS AthleteCount
    FROM olympic_medals
    WHERE Year > 2016 AND Age > {older}
    GROUP BY Sport
    ORDER BY AthleteCount DESC
    LIMIT 3;
    
    -reason:'older' is ambiguous, older can be 30, 40, 50 or other age
3. Formatting Instructions

- Encapsulate any ambiguous or unclear terms directly within curly braces `{}`.
- Do not include any explanatory text, comments, or additional context in the final SQL output.
- If a user's request has some string match. You need to confidently guess simple string mappings based on clear user instructions.
"""
def clean_multiple_backticks(expression):
   
    return expression.strip("`")
class Ambigioussql:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    




    def Generatsql(self, text):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        p1 = "My table name is  " + self.file_name+" .\n"
        p2 = "The columns in my table are: "+column_names_str+" .\n"
        p4 = "My first three rows of data are:\n"
        p4 += " | ".join(self._df.columns) + "\n"  
        p4 += "\n".join(self._df.head(3).astype(str).apply(lambda row: " | ".join(row), axis=1))  # 添加行数据
        p5="\n"+"My question is: "+text
        promptt = p1 +p2+p4+p5
        print(promptt)
        api_key="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"
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
      
            model="gpt-4o-2024-05-13",
            messages=[
                {
                "role": "system",
                "content": prompt
                },
                {
                "role": "user",
                "content": promptt
                }
            ],
            
            temperature=0.4,
            max_tokens=512,
            top_p=1,
        )
        sql=response.choices[0].message.content
        sql = clean_multiple_backticks(sql)
        sql = sql[3:] if sql.lower().startswith('sql') else sql
        return sql