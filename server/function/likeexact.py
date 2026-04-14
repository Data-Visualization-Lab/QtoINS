import ast
from openai import OpenAI
import json

import pandas as pd
def validate_extract(original_list, extract_list):
    return all(any(e in o for o in original_list) for e in extract_list)
prompt="""
You are given:
- A target word .
- The top 30 most similar strings from this target word.

Your task:
1. From these 30 strings, identify those that are similar in meaning to the target word or phrase.
   - Include direct matches, partial matches, abbreviations, acronyms, synonyms, alternate spellings, common misspellings, transliterations, or well-known short forms.
   - Always consider abbreviations, acronyms, synonyms, brand short forms, or alternate spellings as valid semantic matches. For example, “United States” is equal to “US”, “volkswage” is equal to “vw”, and “mercedes-benz” is equal to “mercedes.”.
   - Also include strings that are only approximately similar in meaning, even if not exact matches (i.e., roughly synonymous or conceptually related).

2. Output your result in the following JSON format:

{
  "Original": [], // Original strings from the provided list that are closest in meaning to the target
  "Extract": []   // Simplified or standardized forms of these matched strings
}

If no matches are found, return both lists as empty arrays.

Example:
Target: "Fiction"
Top 10 most similar strings:
['Fiction', 'Fiction, Historical Fiction', 'Fict.', 'Historical Novel', 'Fiction, Mystery', 'Story', 'Fiction, Alphabet', 'Nonfiction, True Crime', 'Childrens, Fiction', 'novel']

Output:
{
  "Original": ["Fiction", "Fiction, Historical Fiction", "Fict.", "Historical Novel", "Fiction, Mystery", "Fiction, Alphabet", "Childrens, Fiction", "novel", "Story"],
  "Extract": ["Fiction", "Fiction", "Fict.", "Novel", "Fiction", "Fiction", "Fiction", "novel", "Story"]
}
"""
def clean_string(input_string):
    
    input_string = input_string.strip('`')
    
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  
    return input_string.strip()  
class LikeExact:
    def __init__(self, df, file_name):
        self._df = df 
        self.file_name = file_name
    def CheckMeaning(self, question,sql,column_name,column_value,list):
        column_names = self._df.columns
        column_names_str = ', '.join(column_names)


        #p1 = "My table name is  " + self.file_name+" .\n"
        #p2 = "The columns in my table are: "+column_names_str+" .\n"
       # p3="My question is: "+question+" .\n"
       # p4="My sql is: "+sql+" .\n"
        p5="In this task, you only need to address only one ambuguous concept: "+ast.literal_eval(column_value)[0][0]+" .\n"
        p6="the 30 strings that are most similar to "+ast.literal_eval(column_value)[0][0]+" are: "+str(list[0:30])+"\n"
        p7="You must look through all the ambuguous strings in this list and tell me all possible answers."
        p8=" Since the user is not familiar with the specific content of this table, identify strings that are semantically similar to ambiguous value based on the user’s query and extract only the words closest to fuzzy. Always consider **abbreviations, acronyms, synonyms, or alternate spellings** as valid semantic matches.Return the json format only!"
        promptt = p5+p6
        print(promptt)


        api_key=""
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

            temperature=0.5,
            max_tokens=2048,
            top_p=1
          )
          fuzzy_recommend=response.choices[0].message.content
          print(fuzzy_recommend)
          fuzzy_recommend = clean_string(fuzzy_recommend)
          fuzzy_recommend = json.loads(fuzzy_recommend)
          if validate_extract(list[0:30], fuzzy_recommend['Extract']):

              break
        return fuzzy_recommend