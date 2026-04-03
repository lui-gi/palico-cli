import argparse
import sys

from palico import db

from palico import display, gemini


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


def _dispatch(action: str, data: dict, focused: dict | None) -> dict | None:
    """Execute the action returned by gemini.parse_intent(). Returns new focused project or None."""
    if action == "add_note" and focused:
        db.add_note(focused["id"], data["content"])
    elif action == "set_deadline" and focused:
        db.update_project(focused["id"], deadline=data["date"])
        focused = db.get_project(focused["id"])
    elif action == "create_project":
        focused = db.create_project(data["name"], data.get("description", ""))
    elif action == "switch_project":
        match = db.fuzzy_find_project(data["name_hint"])
        if match:
            focused = match
    return focused


def _focus_project(raw: str, projects: list[dict]) -> dict | None:
    match = db.fuzzy_find_project(raw.strip())
    return match


def run() -> None:
    parser = argparse.ArgumentParser(prog="palico")
    parser.add_argument("--api", metavar="KEY", help="Gemini API key (saved to config)")
    args = parser.parse_args()

    db.init()
    api_key = _ensure_api_key(override=args.api)
    gemini.init(api_key)

    projects = db.get_all_projects()
    display.show_dashboard(projects)

    focused: dict | None = None

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

        if not raw:
            continue

        if raw.lower() in {"exit", "quit", "q"}:
            sys.exit(0)

        # No project focused yet — treat input as project selection.
        if focused is None:
            focused = _focus_project(raw, projects)
            if focused is None:
                # Ask Gemini to handle it (may be "create project" intent).
                result = gemini.parse_intent(raw, None)
                reply = result.get("reply", "")
                focused = _dispatch(result["action"], result.get("data", {}), None)
                if focused is None:
                    display.print_reply(reply if reply else "I couldn't find that project. Try again or say 'start a new project called ...'")
                    continue
                elif reply:
                    display.print_reply(reply)
            # Show project panel with suggestions.
            notes = db.get_notes(focused["id"])
            suggestions = gemini.get_suggestions(focused, notes)
            display.show_project(focused, notes, suggestions)
            display.print_reply(f"You're now focused on {focused['name']}. Chat away.")
            continue

        # Project is focused — parse intent and dispatch.
        notes = db.get_notes(focused["id"])
        result = gemini.parse_intent(raw, focused, notes)
        action = result.get("action", "none")
        data = result.get("data", {})
        reply = result.get("reply", "")

        new_focused = _dispatch(action, data, focused)
        if new_focused is not None:
            focused = new_focused

        if action == "switch_project" and focused:
            notes = db.get_notes(focused["id"])
            suggestions = gemini.get_suggestions(focused, notes)
            display.show_project(focused, notes, suggestions)

        if reply:
            display.print_reply(reply)
