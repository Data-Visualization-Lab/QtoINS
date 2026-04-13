from openai import OpenAI

prompt = """Given the following inputs:

1. Human Query: A user's natural language question, such as:
"list the best-rated horror films from the 1990s"

2. And a phase about the query, such as: "horror"

Your task is to extract and output the original query's core descriptive phrase (usually a genre or key category) .

Example Output:
horror films
"""
class Phase:

    def Generate( goal,sql,Condition):
        if len(Condition[2])== 0:
            return "None"
        promptt = "My original question is: "+goal+" \n"
        promptt += "My condition dictionary is: "+str(Condition[2][0][0])+" \n"
        promptt += "The output should be a single string that represents the core descriptive phrase.\n"
        promptt += "Please provide the output in a clear and concise manner.\n"


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
      
        return content