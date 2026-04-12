
import json

import pandas as pd
from function.SQL2NL_clean import sql2nl
# prompt = """
# You will receive an ambiguous original question and an SQL statement.
# Your task is to rewrite the question into a clear, natural English question that accurately describes what the SQL query does.
#
# For example:
# - Ambiguous question: "Compare the rating for comedy movies in recent years."
# - SQL: "SELECT Title, IMDB_Rating, Rotten_Tomatoes_Rating FROM movies WHERE Genre IN ('Comedy', 'Black Comedy', 'Romantic Comedy') AND Release_Year > 2002;"
# The improved question should be: "Compare the IMDb and Rotten Tomatoes ratings for comedy, black comedy, and romantic comedy films released after 2002."
#
# Please provide only the final improved English question without any explanations or extra text.
# """
def to_full_sentence(data):
    if not data:
        return ""

    query_sentences = []
    for query in data:
        steps = []
        for item in query.get("explanation", []):
            text = item.get("explanation", "").strip()
            if not text:
                continue
            steps.append(text.rstrip("."))

        if steps:
            sentence = ", then ".join(steps)
            sentence = sentence[0].upper() + sentence[1:]
            if not sentence.endswith("."):
                sentence += "."
            query_sentences.append(sentence)

    return " ".join(query_sentences)

class Translate:
    def __init__(self, df, file_name):
        self._df = df
        self.file_name = file_name

    def Final(self, orginalquestion, sql, tree):
        #print("orginalquestion", orginalquestion)
        #column_names = self._df.columns
        #column_names_str = ", ".join(column_names)

        #p1 = "My table name is " + self.file_name + " \n"
       # p2 = "The columns in my table are: " + column_names_str + " \n"
        #p3 = "My original question is: " + orginalquestion + " \n" + "My original sql is: " + sql + " \n"

       # promptt = p1 + p2 + p3

        #api_key = "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"
        #client = OpenAI(api_key=api_key)
        #print(promptt)
       # response = client.chat.completions.create(
        #    model="gpt-4o",
        #    messages=[
        #        {
        #            "role": "system",
        #            "content": prompt,
         #       },
        #        {
        #            "role": "user",
       #             "content": promptt,
       #         },
        #    ],
       #     temperature=0.5,
        #    max_tokens=512,
        #    top_p=1,
       # )
       # final_question = response.choices[0].message.content
       # print(final_question)
       # raw_explanation_data = sql2nl(sql)
       # print("raw_explanation_data", raw_explanation_data)

       # final_question = to_full_sentence(raw_explanation_data)
        #print("final_question", final_question)
        result = sql2nl(tree)
        final_question=""
        for unit in result:
            print('\n' + unit['number'])
            for step in unit['explanation']:
                print('-', step['subexpression'])
                print('  ', step['explanation'])
                final_question+=step['explanation']+'\n'
        return final_question
