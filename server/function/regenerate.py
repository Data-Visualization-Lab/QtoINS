from openai import OpenAI
prompt = """
Your task is to regenerate the SQL statement strictly adhering to DuckDB syntax whenever the previously generated SQL contains syntax errors due to ambiguous concepts encapsulated within curly braces {}.
The Guidelines for ambiguous concepts are as follows:
Guidelines
	•	If there is ambiguity regarding column names, filters, aggregations, or any other aspect, enclose the ambiguous term directly within curly braces {}.
	•	Always specify a definite column name explicitly alongside the ambiguous term within curly braces if ambiguity occurs in the WHERE clause.
	•	Do not provide explanatory text, comments, or additional context.
    •	Ensure each column specified in SELECT that isn't aggregated or doesn't use an aggregate function is also present in GROUP BY.
    •	When using an aggregation function (such as SUM, MAX, COUNT) alongside non-aggregated columns, you must explicitly specify the GROUP BY clause clearly and without ambiguity.
SQL Format
Provide only the SQL statement strictly adhering to DuckDB syntax and ensure it follows this exact structure when ambiguity exists:

The “{}” of the ambigious concept you generated can only appear in the positions shown in the following two examples.
- **Example
  - Table Name: "olympic_medals"
  - Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'
  - **User's question:** “Compare the medals for hockey and skating by country.”  
  - **Generated SQL:**  
    ```sql
    SELECT Country, {medal} FROM olympic_medals WHERE Sport IN ('Hockey', 'Skating');
    ```
- **Example 

  - Table Name: "olympic_medals"
  - Columns: 'Name', 'Sex', 'Age', 'Country', 'Sport', 'Year', 'Bronze Medal', 'Gold Medal', 'Silver Medal', 'Total Medal'
  - **User's question:** “Identify the top 3 older sports with the highest number of athletes after 2016.”  
  - **Generated SQL:**  
    ```sql
    SELECT Sport, COUNT(*) AS AthleteCount
    FROM olympic_medals
    WHERE Year > 2016 AND Age > {older}
    GROUP BY Sport
    ORDER BY AthleteCount DESC
    LIMIT 3;
    ```

Additional Guidelines for SQL Regeneration:
- Analyze the syntax error message provided by the user carefully.
- Do not attempt to clarify or remove ambiguity; maintain ambiguous terms encapsulated directly within curly braces {} exactly as they appeared.
- Adjust only the SQL structure to ensure strict adherence to DuckDB syntax, positioning ambiguous concepts correctly within valid SQL syntax structures.
- Clearly specify definite column names alongside ambiguous terms within curly braces if the syntax error occurs in WHERE clauses.
- Maintain explicit and valid DuckDB SQL syntax, ensuring any ambiguous terms appear syntactically valid.

Allowed Ambiguous Concept Locations:
- SELECT clause (e.g., `SELECT Country, {medal}`)
- WHERE clause (right-hand side of comparisons only, e.g., `WHERE Age > {age}`)
- Ambiguous concepts are NOT allowed in IN lists within the WHERE clause.
- Ambiguous concepts are NOT allowed inside aggregate functions, GROUP BY, HAVING, ORDER BY clauses, or JOIN conditions.

SQL Format:
SQL Format:
Provide only the regenerated SQL statement strictly adhering to DuckDB syntax. Ambiguity encapsulated in {} must remain exactly as provided by the user in allowed locations,
 repositioned appropriately if possible, or explicitly replaced by the most reasonable specific term if repositioning is not feasible.
Example Scenario:
- Previously Generated SQL:
```sql
SELECT Country, {medal}
FROM olympic_medals
WHERE Sport IN ('Hockey', 'Skating')
GROUP BY Country;
Provided Syntax Error Message:
Non-aggregated column '{medal}' must appear in GROUP BY or be aggregated
Correctly Regenerated SQL (by explicitly guessing):

SELECT Country, SUM(Total_Medal)
FROM olympic_medals
WHERE Sport IN ('Hockey', 'Skating')
GROUP BY Country;
Remember:

First attempt repositioning to maintain ambiguity in allowed positions.

Explicitly guess and replace ambiguous concepts only when repositioning cannot fix the syntax error.
You should generate SQL in the simplest and clearest format.
Only modify SQL structure strictly adhering to DuckDB syntax rules based on the provided syntax error.
"""


def clean_multiple_backticks(expression):
   
    return expression.strip("`")
class ReGeneratsql:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    




    def Generate(self, text, syntax_error):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)
        p1 = "My table name is  " + self.file_name+" .\n"
        p2 = "The columns in my table are: "+column_names_str+" .\n"
        p4 = "My first five rows of data are:\n"
        p4 += " | ".join(self._df.columns) + "\n"  
        p4 += "\n".join(self._df.head(5).astype(str).apply(lambda row: " | ".join(row), axis=1))  
        p5="\n"+"My question is: "+text
        p6 = "\n" + "The syntax error message is: " + "\n".join(syntax_error)
        promptt = p1 +p2+p4+p5+p6
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