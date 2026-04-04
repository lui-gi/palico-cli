from __future__ import annotations

import sys
from pathlib import Path

import click

from palico import display, gemini, session


def _ensure_api_key(override: str | None = None) -> str:
    if override:
        return override
    try:
        from palico.secrets import GEMINI_API_KEY
        if GEMINI_API_KEY and GEMINI_API_KEY != "your-api-key-here":
            return GEMINI_API_KEY
    except ImportError:
        pass
    print("Error: add your Gemini API key to palico/secrets.py", file=sys.stderr)
    sys.exit(1)


@click.group()
@click.option("--api", "api_key", metavar="KEY", help="Gemini API key override")
@click.pass_context
def run(ctx: click.Context, api_key: str | None) -> None:
    """Palico — your pentesting and bug bounty companion."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key


@run.command()
@click.argument("question_text")
@click.pass_context
def question(ctx: click.Context, question_text: str) -> None:
    """Answer a security or pentesting question in 2-3 sentences."""
    gemini.init(_ensure_api_key(ctx.obj.get("api_key")))
    answer = gemini.answer_question(question_text)
    display.show_answer(question_text, answer)


@run.command()
@click.argument("engagement_name")
@click.pass_context
def start(ctx: click.Context, engagement_name: str) -> None:
    """Generate a tailored pentesting checklist for an engagement."""
    gemini.init(_ensure_api_key(ctx.obj.get("api_key")))
    try:
        target_info = display.prompt_target_info(engagement_name)
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)
    checklist = gemini.generate_checklist(engagement_name, target_info)
    display.show_checklist(engagement_name, checklist)


@run.command()
@click.option("--session", "-s", "session_name", default="default", show_default=True,
              help="Session name (isolate by engagement)")
@click.option("--fresh", is_flag=True, help="Start a new session (wipes history)")
@click.pass_context
def chat(ctx: click.Context, session_name: str, fresh: bool) -> None:
    """Interactive chat with persistent memory across sessions."""
    gemini.init(_ensure_api_key(ctx.obj.get("api_key")))

    history = [] if fresh else session.load(session_name)
    if fresh:
        session.clear(session_name)

    display.show_chat_header(session_name, len(history))

    _HELP = (
        "  /save <file.md>   write last reply to a file\n"
        "  /clear            clear session history\n"
        "  /sessions         list all saved sessions\n"
        "  /help             show this help\n"
        "  exit / quit       leave the chat"
    )

    last_reply: str = ""

    while True:
        try:
            user_input = input(f"[{session_name}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "/exit", "/quit"}:
            break

        if user_input.lower() == "/help":
            print(_HELP)
            continue

        if user_input.lower() == "/sessions":
            names = session.list_sessions()
            print("  " + ("  ".join(names) if names else "(none)"))
            continue

        if user_input.lower() == "/clear":
            history = []
            session.clear(session_name)
            print(f"  Session '{session_name}' cleared.")
            continue

        if user_input.lower().startswith("/save "):
            filename = user_input[6:].strip()
            if not last_reply:
                print("  Nothing to save yet.")
            else:
                _write_file(filename, last_reply)
            continue

        # Truncate to last 40 turns before sending
        truncated = history[-40:]
        result = gemini.chat_turn(truncated, user_input)

        if result.text:
            display.show_chat_reply(result.text)
            last_reply = result.text

        for call in result.tool_calls:
            outcome = _dispatch_tool(call, session_name, history)
            display.show_tool_result(call["name"], outcome)

        history.append({"role": "user", "text": user_input})
        if result.text:
            history.append({"role": "model", "text": result.text})
        session.save(session_name, history)


def _dispatch_tool(call: dict, session_name: str, history: list) -> str:
    name = call["name"]
    args = call.get("args", {})
    if name == "save_to_file":
        path = Path(args["filename"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"] + "\n")
        return f"Written to {path}"
    if name == "append_to_file":
        path = Path(args["filename"])
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write("\n" + args["content"] + "\n")
        return f"Appended to {path}"
    if name == "clear_session":
        history.clear()
        session.clear(session_name)
        return f"Session '{session_name}' cleared"
    if name == "list_sessions":
        names = session.list_sessions()
        return ", ".join(names) if names else "(no saved sessions)"
    return f"Unknown tool: {name}"


def _write_file(filename: str, content: str) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n")
    print(f"  Written to {path}")


@run.command()
def owasp() -> None:
    """Display the OWASP Top 10."""
    display.show_owasp()
