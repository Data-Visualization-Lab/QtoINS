from openai import OpenAI
import json

import pandas as pd
prompt="""
You are an expert in modifying Vega-Lite specifications. Given a partial Vega-Lite JSON specification and a user's modification request, generate a complete Vega-Lite JSON specification incorporating the requested changes.

### Input:
- A partial Vega-Lite specification.
- A user's modification request describing the desired changes.

### Output:
Return only the complete modified Vega-Lite JSON specification as a Python string. Do not include any explanations or additional text.

### Example:

#### **Input:**
**Partial Vega-Lite Specification:**
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "A simple bar chart with embedded data.",
  "data": {
    "values": [
      {"category": "A", "value": 1},
      {"category": "B", "value": 55},
      {"category": "C", "value": 43}
    ]
  },
  "mark": "bar",
  "encoding": {
    "x": {"field": "category", "type": "ordinal"},
    "y": {"field": "value", "type": "quantitative"}
  }
}

**User's Modification Request:**  
- Change the chart to a line chart and add the title "Line Chart Example".

#### **Output:**
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "description": "A simple line chart with embedded data.",
  "title": "Line Chart Example",
  "data": {
    "values": [
      {"category": "A", "value": 1},
      {"category": "B", "value": 55},
      {"category": "C", "value": 43}
    ]
  },
  "mark": "line",
  "encoding": {
    "x": {"field": "category", "type": "ordinal"},
    "y": {"field": "value", "type": "quantitative"}
  }
}

### Additional Guidelines:
- Ensure that the modified Vega-Lite JSON is valid and follows the schema.
- Only output the modified Vega-Lite JSON specification as a Python string.
- Do not provide explanations, comments, or any extra text beyond the JSON output."""

def clean_string(input_string):
    
    input_string = input_string.strip('`')
    
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  
    return input_string.strip()  

class Changechart:
    def Generate(self, request,vegalite):
        p1="You are an expert in modifying Vega-Lite specifications. user's modification request is: " +request+"\n"
        p2="The partial Vega-Lite specification is: " +json.dumps(vegalite)

        

        promptt =p1+p2
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
        print(content)
      
        return content