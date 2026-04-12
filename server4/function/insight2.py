import base64
import io
import json
import os
import re
import tempfile
import regex
import altair as alt
import vl_convert as vlc
import time
from openai import OpenAI


def extract_json(text):
    json_pattern = regex.findall(r"\{(?:[^{}]|(?R))*\}", text)
    for match in json_pattern:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    return None


def clean_string(input_string):
    
    input_string = input_string.strip("`")
    
    if input_string.lower().startswith("json"):
        input_string = input_string[4:].strip()  
    return input_string.strip()  


class Insight2:
    def __init__(self, df, file_name):
        self._df = df
        self.file_name = file_name

    def story(self, question, vegalite_spec, all_file):
        api_key = "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"

        client = OpenAI(api_key=api_key)
        instructions = """
        You will be given a chart image and its corresponding CSV data.  
        Your role is a visualization expert, and your task is to analyze both sources and produce insightful conclusions in a well-structured JSON format.

        Rules:
        - Output must be a valid JSON object with exactly five keys:  
        1. "Observation of the Chart"  
        2. "Visual Trend Analysis"  
        3. "Statistical Analysis Summary"  
        4. "Integrated Findings"  
        5. "Overall Insight Summary"  
        - You must think step by step, but only output the final JSON (do not show intermediate reasoning).  
        - Do not artificially highlight the absence of features (e.g., no legend, no missing values, no anomalies).  
        - Each value must be a natural, flowing sentence (no bullet points, no lists).  
        - The five keys together must form one coherent and complete paragraph when their contents are joined in order, without any repetition or redundancy. Each key should add unique information that naturally extends the previous one.  

        Key instructions:  
        1. Observation of the Chart: Describe the specific chart type, axes (x and y), and categories/legends if present.  
        2. Visual Trend Analysis: Summarize visual patterns such as trends, clusters, or anomalies that clearly stand out.  
        3. Statistical Analysis Summary: Present the computed figures such as averages, medians, standard deviations, quartiles, correlations, and outliers in a natural sentence, for example: “On average, sales reached X while most values clustered around Y, with a noticeable spread of Z.” Do not explain how these figures relate to the visual trends. If the dataset is small, still provide a natural-sounding numerical summary to ensure smooth paragraph flow rather than sounding mechanical.  
        4. Integrated Findings: Compare the statistical and visual findings. If they are consistent, summarize in one very short and simple English sentence to avoid repetition but still highlight any outliers or unusual deviations with possible explanations. If they are inconsistent, explain the differences and also point out any anomalies.
        5. Overall Insight Summary: Provide a concise implication or reasoning that goes beyond description, suggesting possible causes, behaviors, or business implications, and ensure it is not just a restatement of previous findings but a small interpretative or predictive leap.

        The final output should read like a concise, logically flowing short report where the five sentences combine into one non-repetitive paragraph.
            {
                "Observation of the Chart": "The chart is a bar chart with quarters on the x-axis and average delivery times in days on the y-axis, with two distinct colors representing Standard Shipping and Express Shipping.",
                "Visual Trend Analysis": "The bars reveal that Standard Shipping delivery times gradually decreased across the four quarters, while Express Shipping stayed consistently low except for a modest rise in the final quarter.",
                "Statistical Analysis Summary": "Standard Shipping averaged 5.8 days with most results close to 6 and a spread of 0.5, while Express Shipping averaged 2.4 days with a tighter spread of 0.3 but showed an outlier of 3.0 days in Q4.",
                "Integrated Findings": "The numbers align with the visual trends, with the Q4 Express anomaly pointing to a temporary disruption such as seasonal demand or capacity strain.",
                "Overall Insight Summary": "This indicates that operational improvements are effectively reducing Standard Shipping delays, while Express Shipping requires careful oversight during peak demand to maintain its reliability."
            }
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        )
        tmp_path = tmp.name
        self._df.to_csv(tmp_path, index=False)
        tmp.close()
        print("Temporary CSV saved to:", tmp_path)
        file_resp = client.files.create(file=open(tmp_path, "rb"), purpose="assistants")
        file_id = file_resp.id
        print("Uploaded CSV as file_id:", file_id)
        png_bytes = vlc.vegalite_to_png(vegalite_spec, vl_version="5.8", scale=3)
        mime = "image/png"
        b64 = base64.b64encode(png_bytes).decode()
        data_url = f"data:{mime};base64,{b64}"

        prompt = (
            f"My question is {question}.\n"
            # f"{all_file_uploaded.id} is the table that the user is asking about.\n"
            f"Please combine the uploaded image and CSV file to help me derive insights."
        )

        response = client.responses.create(
            model="gpt-4o",
            tools=[
                {
                    "type": "code_interpreter",
                    "container": {"type": "auto", "file_ids": [file_id]},
                }
            ],
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            instructions=instructions,
            tool_choice="required",
        )
        text_content = response.output_text
        print("Response from OpenAI:", text_content)
        text_content = clean_string(text_content)
        print(text_content)
        text_content = extract_json(text_content)
        return text_content
