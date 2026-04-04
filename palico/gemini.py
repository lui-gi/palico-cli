from __future__ import annotations

import json

from google import genai
from google.genai import types

_client: genai.Client | None = None

_QUESTION_SYSTEM_PROMPT = (
    "You are a cybersecurity expert and pentesting mentor embedded in a terminal CLI. "
    "Answer the following security or pentesting question in exactly 2-3 sentences. "
    "Be precise and technical. Do not pad the answer. Do not use bullet points. "
    "Focus on practical, actionable insight a pentester would actually use."
)

_CHECKLIST_SYSTEM_PROMPT = (
    "You are an expert penetration tester generating a structured pentesting checklist. "
    "Return ONLY valid JSON — a list of objects with this exact shape:\n"
    '[{"category": "string", "items": ["string", ...]}]\n\n'
    "Categories to include (adapt items to the target):\n"
    "- Reconnaissance\n"
    "- Authentication & Authorization\n"
    "- Input Validation & Injection\n"
    "- Business Logic\n"
    "- Session Management\n"
    "- Sensitive Data Exposure\n"
    "- Infrastructure & Configuration\n\n"
    "Keep each item short and action-oriented (imperative verb). "
    "Tailor items specifically to the tech stack and app type provided. "
    "Return only the JSON array, no markdown fences."
)


def init(api_key: str) -> None:
    global _client
    _client = genai.Client(api_key=api_key)


def answer_question(question_text: str) -> str:
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=question_text,
            config=types.GenerateContentConfig(
                system_instruction=_QUESTION_SYSTEM_PROMPT,
            ),
        )
        return response.text.strip()
    except Exception as e:
        return f"Error reaching Gemini: {e}"


def generate_checklist(engagement_name: str, target_info: dict) -> list[dict]:
    user_message = (
        f"Engagement: {engagement_name}\n"
        f"Target URL: {target_info['url']}\n"
        f"App type: {target_info['app_type']}\n"
        f"Tech stack: {target_info['tech_stack']}\n"
        f"Auth type: {target_info['auth_type']}\n"
        f"Scope notes: {target_info['scope_notes']}"
    )
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_CHECKLIST_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text.strip())
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        return [{"category": "Error", "items": [f"Could not generate checklist: {e}"]}]
