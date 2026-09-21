import io
import json
import re
import altair as alt
import vl_convert as vlc
import time
from openai import OpenAI
import tempfile
import regex
import base64

def extract_json(text):
    json_pattern = regex.findall(r'\{(?:[^{}]|(?R))*\}', text)
    for match in json_pattern:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return None

def clean_string(input_string):
    
    cleaned = input_string.strip('`').strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].strip()
    return cleaned

class ChangeInsight5:
    def __init__(self, df, file_name):
        
        self._df = df 
        self.file_name = file_name

    def newstory(self, all_but_last, last_key, question, vegalite_spec):
        instructions = """
You will receive: the user's question, a CSV extracted for that question, and a pre-generated chart image.

TASK
1) Use Python to analyze the CSV.
2) Combine CSV analysis with the given chart image to produce concise, meaningful insights.
3) You MUST run a brief web search to add relevant domain context and cite it inline (mention the source name + date). Use only stable, non-speculative facts.

OUTPUT FORMAT (HARD REQUIREMENT)
- Reply as a single well-formed JSON object.
- Each top-level key = one logical reasoning step.
- The FIRST key must be the concept the user wants to extend (e.g., "Statistical Analysis Summary").
- Finish with "Overall Insight Summary".
- If a better chart would help, add a "vegalite" key (see STRICT RULES below).
- Do NOT repeat insights already supplied by the user.
- No extra text, no markdown outside the JSON.


STRICT RULES FOR "vegalite"
A) RAW DATA ONLY
- "data.values" must contain the untouched raw CSV rows exactly as-is (I will alternative them later).
- Every field referenced in "encoding" or "transform" MUST appear verbatim in the CSV header.
- You may use simple "transform" steps, but ONLY on existing fields.
B) MINIMAL SPEC (NO INTERACTIVITY OR STYLING)
- Allowed top-level keys inside "vegalite": "data", "mark", "encoding", "transform", "title".
- Allowed "mark" values: "line", "bar", "point", or "area".
- "width" and "height" MUST be positive integers. Do not use strings like "container".
- PROHIBITED keys anywhere: "tooltip", "selection", "params", "resolve", "config", "legend", "scale.domainMid", "condition", "test", "autosize", "view", "projection", "params".
- PROHIBITED expressions: any "test" or conditional color/size/opacity; any field not in CSV (e.g., "Outlier").
- PROHIBITED transformations: window, joinaggregate, lookup, regression, loess, aggregate on derived fields.
- Color: either omit color entirely, or map "color" directly to an existing categorical field without conditionals.

C) COMPLIANCE AUDIT (MANDATORY)
Before returning the final JSON, you MUST:
- Validate that no PROHIBITED keys/expressions are present.
- Validate all referenced fields exist in the CSV header.
- Validate width/height are integers.
- If ANY check fails, REVISE the "vegalite" until all checks pass.

D) EXECUTION GUARANTEE (HARD REQUIREMENT)
- The "vegalite" spec MUST be fully self-contained and directly executable.
- After I replace only the "data.values" rows with my own CSV rows (keeping headers unchanged), the chart MUST render without any further edits, configurations, or additional files.

WEB SEARCH REQUIREMENT
- Perform a brief web search for domain background (e.g., typical ranges, benchmarks, seasonality).
- Incorporate at most 2–3 factual points that support/contrast the CSV findings.
- Paraphrase; do not paste long quotes.
- Mention the source name and (Month YYYY). Avoid paywalled or untrusted blogs.

JSON SHAPE EXAMPLE (SKELETON ONLY)
{
  "Statistical Analysis Summary": "<concise stats from Python on the CSV>",
  "Integrated Findings": "<what the chart + stats say together, with brief domain context>",
  "Overall Insight Summary": "<one-paragraph conclusion>",
  "vegalite": {
    "mark": "line",
    "encoding": {
      "x": {"field": "<existing_csv_field>", "type": "temporal", "title": "<x title>"},
      "y": {"field": "<existing_csv_field>", "type": "quantitative", "title": "<y title>"}
    }
  }
}
        """
      
        api_key=""
        client = OpenAI(api_key=api_key)
       
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        tmp_path = tmp.name
        self._df.to_csv(tmp_path, index=False)
        tmp.close()
        print("Temporary CSV saved to:", tmp_path)
        file_resp = client.files.create(
            file=open(tmp_path, "rb"),
            purpose="assistants"
        )
        file_id = file_resp.id
        print("Uploaded CSV as file_id:", file_id)
        png_bytes = vlc.vegalite_to_png(vegalite_spec, vl_version="5.8", scale=3)
        mime = "image/png"
        b64 = base64.b64encode(png_bytes).decode()
        data_url = f"data:{mime};base64,{b64}"

        insight_chain = ""
        for index, item in enumerate(all_but_last):
            if index == 0:
                insight_chain += f"I first inferred that {item['key']} has the content \"{item['value']}\".\n"
            else:
                insight_chain += f"Then I inferred that {item['key']} has the content \"{item['value']}\".\n"
                     

        vegalite_spec["data"]["values"] = vegalite_spec["data"]["values"][:3]
        prompt = (
            f"Now I already have the following logical reasoning chain:\n"
            f"{insight_chain}\n"
            f"Now you need to think {last_key} then continue to carry out logical reasoning. Please combine the uploaded image and CSV file to help me derive insights. "
            f"I want the insights to be concise, insightful, and meaningful.\n"
            f"My chart is as follows:\n" + str(vegalite_spec) +
            f"Please use {last_key} as your first key and use chain of thought to generate the next insight. Let's think step by step."
        )



        response = client.responses.create(
                    model="gpt-4o",
                    tools=[
                        {
                            "type": "code_interpreter",
                                    "container": {
                                "type": "auto",
                                "file_ids": [file_id]
                            }
                        },{"type": "web_search_preview"}
                    ],
                    input=[
                        {
                            "role": "user",
                            "content": [
                                { "type": "input_text", "text": prompt },
                                {
                                    "type": "input_image",
                                    "image_url":data_url
                                }
                            ]
                        }
                    ],
                    instructions=instructions,
                    tool_choice="required",
                )
        text_content=response.output_text

        cleaned_text = clean_string(text_content)
        print("Cleaned text:", cleaned_text)
        extracted_json = extract_json(cleaned_text)
        print("Extracted JSON:", extracted_json)
        return extracted_json
