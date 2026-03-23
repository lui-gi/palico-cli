import json
import sys
from pathlib import Path

from palico import db

CONFIG_DIR = Path.home() / ".palico"
CONFIG_PATH = CONFIG_DIR / "config.json"

# These are imported lazily after T2/T3 are done; stubs let the file parse now.
try:
    from palico import display, gemini
    _FULL = True
except ImportError:
    _FULL = False


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


def _ensure_api_key(cfg: dict) -> str:
    if "gemini_api_key" in cfg:
        return cfg["gemini_api_key"]
    key = display.prompt_api_key()
    cfg["gemini_api_key"] = key
    _save_config(cfg)
    return key


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
    db.init()
    cfg = _load_config()
    api_key = _ensure_api_key(cfg)
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
                if reply:
                    display.print_reply(reply)
                if focused is None:
                    display.print_reply("I couldn't find that project. Try again or say 'start a new project called ...'")
                    continue
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
