from __future__ import annotations

import json
from dataclasses import dataclass, field

from google import genai
from google.genai import types

_client: genai.Client | None = None

_QUESTION_SYSTEM_PROMPT = (
    "You are a cybersecurity expert and pentesting mentor embedded in a terminal CLI. "
    "Answer the following security or pentesting question in exactly 2-3 sentences. "
    "Be precise and technical. Do not pad the answer. Do not use bullet points. "
    "Focus on practical, actionable insight a pentester would actually use."
)

_CHAT_SYSTEM_PROMPT = (
    "You are Palico, an elite bug bounty hunter and penetration tester embedded in a terminal CLI. "
    "You have deep expertise in web app security, network pentesting, OSINT, and vulnerability research. "
    "You help the user during live engagements: answer questions, suggest attack paths, explain findings, "
    "and help document results. Be concise and technical. "
    "You have tools available to save notes to files, clear history, and list sessions — "
    "use them whenever the user's intent matches, even if they phrase it informally."
)

_CHAT_TOOLS = [types.Tool(function_declarations=[
    types.FunctionDeclaration(
        name="save_to_file",
        description="Write markdown content to a file, overwriting it if it exists. Use when the user wants to save, write, or dump something to a file.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "filename": types.Schema(type="STRING", description="File path to write to, e.g. notes.md or recon/findings.md"),
                "content":  types.Schema(type="STRING", description="Full markdown content to write to the file"),
            },
            required=["filename", "content"],
        ),
    ),
    types.FunctionDeclaration(
        name="append_to_file",
        description="Append markdown content to an existing file (or create it). Use when the user wants to add to or update existing notes.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "filename": types.Schema(type="STRING", description="File path to append to"),
                "content":  types.Schema(type="STRING", description="Markdown content to append"),
            },
            required=["filename", "content"],
        ),
    ),
    types.FunctionDeclaration(
        name="clear_session",
        description="Wipe the current conversation history. Use when the user wants to start fresh or forget the conversation.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
    types.FunctionDeclaration(
        name="list_sessions",
        description="Return the names of all saved chat sessions.",
        parameters=types.Schema(type="OBJECT", properties={}),
    ),
])]


@dataclass
class ChatResult:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)


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


def chat_turn(history: list[dict], message: str) -> ChatResult:
    """Send a message with full conversation history. Returns text and/or tool calls."""
    contents = []
    for turn in history:
        contents.append(
            types.Content(role=turn["role"], parts=[types.Part(text=turn["text"])])
        )
    contents.append(types.Content(role="user", parts=[types.Part(text=message)]))
    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=_CHAT_SYSTEM_PROMPT,
                tools=_CHAT_TOOLS,
            ),
        )
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        for part in response.candidates[0].content.parts:
            if part.function_call:
                tool_calls.append({"name": part.function_call.name, "args": dict(part.function_call.args)})
            elif part.text:
                text_parts.append(part.text)
        return ChatResult(text="".join(text_parts).strip(), tool_calls=tool_calls)
    except Exception as e:
        return ChatResult(text=f"Error reaching Gemini: {e}")


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
