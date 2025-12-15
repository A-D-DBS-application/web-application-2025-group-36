# app/services/ai_analysis.py

import json
import re
from flask import current_app
import google.generativeai as genai


def clean_json_output(text: str) -> str:
    """
    Removes markdown code fences (```json ... ```)
    so the output becomes valid JSON for json.loads().
    """
    # Remove the opening ```json or ```python or ``` blocks
    text = re.sub(r"```json", "", text, flags=re.IGNORECASE)
    text = re.sub(r"```python", "", text, flags=re.IGNORECASE)

    # Remove generic ```
    text = text.replace("```", "")

    return text.strip()


def analyze_paper_text(full_text: str):

    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: GEMINI_API_KEY missing.")
        return None

    # Configure Gemini
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("models/gemini-flash-latest")

    prompt = f"""
    You are an expert scientific evaluator.
    Analyze the following research paper text.

    Respond ONLY with valid JSON in this exact schema:
    - No trailing commas
    - No markdown
    - No explanations

    {{
        "business_score": number,
        "academic_score": number,
        "summary": "string",
        "strengths": "string",
        "weaknesses": "string"
    }}

    Paper text:
    {full_text}
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2}
        )

        raw = response.text

        # --------------------------------
        # 🔧 HARDENED JSON CLEAN & PARSE
        # --------------------------------

        # 1️⃣ Remove markdown/code fences
        cleaned = clean_json_output(raw)

        # 2️⃣ Extract FIRST JSON object only
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            print("❌ No JSON object found")
            print("Raw output:", cleaned)
            return None

        json_text = match.group()

        # 3️⃣ REMOVE ALL TRAILING COMMAS (Gemini-safe)
        while re.search(r",\s*[}\]]", json_text):
            json_text = re.sub(r",\s*([}\]])", r"\1", json_text)

        # 4️⃣ Final parse
        try:
            return json.loads(json_text)
        except Exception as e:
            print("❌ JSON decode failed:", e)
            print("Raw cleaned output:", json_text)
            return None

    except Exception as e:
        print("❌ Gemini API call failed:", e)
        return None
