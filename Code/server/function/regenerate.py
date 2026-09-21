from openai import OpenAI
prompt = """
Your task is to regenerate an SQL statement adhering to DuckDB syntax and the placeholder rules below, based on the user's question, the previous SQL, and its syntax error.
Preserve ambiguous concepts directly within curly braces {} without guessing the user's intent. Fix the reported error while keeping valid calculations and existing ambiguity.
STRICT POSITION RULES FOR {}
- The {} placeholder is ONLY allowed in the following cases but could appear multiple times:
  1. In the SELECT clause, replacing a non-aggregated column name (e.g., SELECT {medal}). The user may select multiple columns for this placeholder.
  2. As the argument of MIN, MAX, AVG, SUM, or COUNT in the SELECT clause (e.g., MAX({medal})). Each placeholder must resolve to exactly one column.
  3. In the GROUP BY clause, replacing a column name (e.g., GROUP BY {region}). Each placeholder must resolve to exactly one column. If the same concept appears in SELECT and GROUP BY, use exactly the same placeholder text so both positions resolve to the same single column.
  4. In the WHERE clause, replacing a literal value explicitly paired with a specific numeric column. It must appear on the right-hand side of >, >=, <, or <=; the '=' operator is not allowed for placeholders.
- Do not put placeholders in LIMIT, ORDER BY, HAVING, JOIN conditions, IN lists, or LIKE patterns. Ordinary LIMIT values, ORDER BY aliases, IN lists, and LIKE patterns remain allowed.
- For WHERE comparisons, put an actual column on the left and a literal value on the right. For example, Genre = 'Comedy' is valid; 'Comedy' = Genre and Age > Year are not. AND and OR may combine conditions. IN lists and BETWEEN bounds must contain values.
- Keep valid calculations such as SELECT Price * Quantity AS Revenue FROM sales; and COUNT(*). Do not replace an ambiguous column with a guessed definite column.
- When aggregated and non-aggregated columns are selected together, include the non-aggregated columns in GROUP BY. Placeholders are allowed in GROUP BY as described above.

- Example
  - Table Name: "olympic_medals"
  - Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'
  - User's question: “Compare the medals for hockey and skating by country.”
  - Generated SQL:
    SELECT Country, {medal} FROM olympic_medals WHERE Sport IN ('Hockey', 'Skating');
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
- Example
  - Table Name: "olympic_medals"
  - User's question: "What is the maximum medal count?"
  - Generated SQL:
    SELECT MAX({medal}) FROM olympic_medals;
  -reason: The user selects one medal column for MAX.
- Example
  - Table Name: "olympic_medals"
  - User's question: "Count athletes by region."
  - Generated SQL:
    SELECT {region}, COUNT(*) AS AthleteCount FROM olympic_medals GROUP BY {region};
  -reason: The user selects one region column, shared by SELECT and GROUP BY.

Formatting Instructions
- Analyze the provided syntax error and change only what is needed to fix the SQL.
- Keep ambiguous terms in allowed locations, repositioning them if needed without replacing them with guessed columns or values.
- Do not include explanatory text, comments, code fences, or additional context in the final SQL output.
- For clear string matches, use the corresponding literal value from the user's instructions.
"""


def clean_multiple_backticks(expression):
   
    return expression.strip("`")
class ReGeneratsql:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    




    def Generate(self, text, syntax_error, sql=None):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        p1 = "My table name is  " + self.file_name+" .\n"
        p2 = "The columns in my table are: "+column_names_str+" .\n"
        p4 = "My first five rows of data are:\n"
        p4 += " | ".join(self._df.columns) + "\n"  
        p4 += "\n".join(self._df.head(5).astype(str).apply(lambda row: " | ".join(row), axis=1))  
        p5="\n"+"My question is: "+text
        p6 = "\n" + "The syntax error message is: " + str(syntax_error)
        p7 = "\n" + "The previous SQL is: " + sql if sql is not None else ""
        promptt = p1 +p2+p4+p5+p6+p7
        print(promptt)
        api_key=""
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
                "content": promptt
                }
            ],
            
            temperature=1,
            max_tokens=512,
            top_p=1,

        )

        sql=response.choices[0].message.content
        sql = clean_multiple_backticks(sql)
        sql = sql[3:] if sql.lower().startswith('sql') else sql

        return sql
