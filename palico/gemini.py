import json
from datetime import date

from google import genai
from google.genai import types

_client: genai.Client | None = None


def init(api_key: str) -> None:
    global _client
    _client = genai.Client(api_key=api_key)


def parse_intent(user_message: str, focused_project: dict | None, notes: list[dict] | None = None) -> dict:
    today = date.today().isoformat()

    if focused_project:
        name = focused_project.get("name", "")
        deadline = focused_project.get("deadline") or "none"
        notes_raw = notes or []
        notes_text = "\n".join(f"• {n['content']}" for n in notes_raw) or "(none)"
    else:
        name = ""
        deadline = "none"
        notes_text = "(none)"

    system_prompt = f"""You are palico, a personal project assistant in the terminal.
Today's date is {today}.
Focused project: "{name}" (deadline: {deadline}).
Notes: {notes_text}

When the user says something to persist, respond ONLY with JSON:
{{
  "action": "add_note" | "set_deadline" | "create_project" | "switch_project" | "none",
  "data": {{ ... }},
  "reply": "..."
}}

add_note:       data = {{ "content": "..." }}
set_deadline:   data = {{ "date": "YYYY-MM-DD" }}
create_project: data = {{ "name": "...", "description": "..." }}
switch_project: data = {{ "name_hint": "..." }}
none:           data = {{}}

Resolve relative dates against today. Return only valid JSON."""

    try:
        response = _client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
            ),
        )
        text = response.text.strip()
        result = json.loads(text)
        return {
            "action": result.get("action", "none"),
            "data": result.get("data", {}),
            "reply": result.get("reply", ""),
        }
    except Exception as e:
        return {"action": "none", "data": {}, "reply": f"Sorry, I couldn't reach the AI ({e}). Try again."}


def get_suggestions(project: dict, notes: list[dict]) -> list[str]:
    name = project.get("name", "")
    deadline = project.get("deadline") or "none"
    notes_text = "\n".join(f"• {n['content']}" for n in notes) or "(none)"

    prompt = f"""Given notes on "{name}" (deadline: {deadline}):
{notes_text}

Give exactly 1-2 short, actionable suggestions. Return as a JSON array of strings."""

    try:
        response = _client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        text = response.text.strip()
        suggestions = json.loads(text)
        if isinstance(suggestions, list):
            return [str(s) for s in suggestions[:2]]
        return []
    except Exception:
        return []
