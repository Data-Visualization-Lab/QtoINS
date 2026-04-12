from openai import OpenAI
import json
import ast
import pandas as pd

prompt="""
You are tasked with analyzing a user's query regarding an SQL statement and determining whether a specific string used within an SQL statement's condition is vague or ambiguous. The user is unaware of the actual content within the database, so your judgment should be based on semantic similarity and reasonable alternatives that might match the user's intent.

Instructions: Based on the user's query, table structure, and the provided column, analyze the top strings that are semantically most similar to the target string. If you determine that the string the user provided is ambiguous or fuzzy—meaning that there are other strings in the column that could reasonably fulfill the user's intent—set the flag to true and provide those alternative strings in the Fuzzy_List.

Consider broadly synonymous or contextually similar terms, especially when dealing with categorical, geographic, or genre-related queries. The alternatives you choose should reasonably capture the user's original intent, even if they are not identical to the user's input.

If no suitable alternatives exist that align with the intended meaning, set the flag to false without an additional list.
I will give you  three examples:
This is the first example:

Now I have a table named books and this table has these columns: Rank, book title, book price, rating, author,year of publication, genre, url.
My question is :I want to know which books are in the 'Fiction' genre. Can you show me the book title, author, and URL?
My sql is: SELECT `book title`, author, url FROM books WHERE genre = 'Fiction';
In the "genre" column, the 10 strings that are most similar to "Fiction" are:
['Fiction', 'Fiction, Historical Fiction', 'Historical Fiction', 'Fiction, Mystery', 'Nonfiction', 'Fiction, Alphabet', 'Nonfiction, True Crime', 'Childrens, Fiction', 'Fantasy', 'Autobiography']
you need return this json format
{
  "flag": true,
  "Fuzzy_List":['Fiction', 'Fiction, Historical Fiction', 'Historical Fiction', 'Fiction, Mystery', 'Fiction, Alphabet', 'Childrens, Fiction']
}

This is the second example:
Now I have a table named books and this table has these columns: Rank, book title, book price, rating, author,year of publication, genre, url.
My question is :I want to know which books are in the 'cartoon' genre. Can you show me the book title, author, and URL?
My sql is: SELECT `book title`, author, url FROM books WHERE genre = 'cartoon';
In the "genre" column, the 10 strings that are most similar to "cartoon" are:
['Fiction', 'Fiction, Historical Fiction', 'Historical Fiction', 'Fiction, Mystery', 'Nonfiction', 'Fiction, Alphabet', 'Nonfiction, True Crime', 'Childrens, Fiction', 'Fantasy', 'Autobiography']
you need return this json format
{
  "flag": False
}


This is the third example:
Now I have a table named books and this table has these columns: Rank, book title, book price, rating, author,year of publication, genre, url.
My question is :There is a book called 'hatchet' Can you help me find its detailed information?"
My sql is: SELECT * FROM books WHERE `book title` = 'hatchet';
In the "book title" column, the 10 strings that are most similar to "Hatchet" are:['Hatchet',
 'The Wager: A Tale of Shipwreck, Mutiny and Murder',
 'Things We Never Got Over (Knockemout)',
 'Unwoke: How to Defeat Cultural Marxism in America',
 'A Court of Thorns and Roses (A Court of Thorns and Roses, 1)',
 'A Court of Wings and Ruin (A Court of Thorns and Roses, 3)',
 'The Housemaid',
 'A Court of Thorns and Roses Paperback Box Set (5 books)',
 "Don't Let the Pigeon Drive the Sleigh!",
 'Killers of the Flower Moon: The Osage Murders and the Birth of the FBI']

you need return this json format
{
  "flag": true,
  "Fuzzy_List":['Hatchet']
}
Remember, the user does not have specific knowledge of the table's contents. Therefore, always consider whether the user's query could reasonably include other semantically similar strings present in the data.

"""

def clean_string(input_string):
    # 移除开头和结尾的反引号
    input_string = input_string.strip('`')
    # 如果移除反引号后，字符串开头是 json，移除它
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  # 移除开头的 json 并去掉多余的空格
    return input_string.strip()  # 再次清理两边空格
class StringCheckMeaning:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name

    def CheckMeaning(self,sql,question, column_name,column_value,list):
        column_names = self._df.columns
        print(type(column_value))
        column_names_str = ', '.join(column_names)


        column_value = ast.literal_eval(column_value)

        column_value = ', '.join(f"'{item}'" for item in column_value[0][:-1]) + ', '
        p1 = "I have a database table, the table name is " + self.file_name + " ,and"
        p2 = " The columns in my table are:"
        p3="My question is: "
        p4=" My sql is: "
        p5="In the "
        p6=" column, the 10 strings that are most similar to "
        p7=" are: "
        p8="\n"+"You only need to detect the content most similar to"+ column_value+"\n"+"Please return only the specific content in JSON format without any additional information, not even the word JSON."
        print(column_value)
        promptt = p1 +p2+column_names_str +p3+ question+"\n"+p4+sql+p5+column_name+p6+column_value+p7+json.dumps(list)+p8
        print(promptt)
      

        api_key="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"
        client = OpenAI(api_key=api_key)
        while True:
            
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
            max_tokens=1024,
            top_p=1
            )
            content=response.choices[0].message.content
            print(content)
            content=clean_string(content)
            content = json.loads(content)
            print(content)
            print(column_value)
            if content.get("flag") == False:
                break
            is_subset = set(content['Fuzzy_List']).issubset(set(list))
            print(is_subset)
            if is_subset or content.get("flag") == False:
                break
            print(content)
        return content