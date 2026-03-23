# palico-cli — Design Spec

## What it is

palico is a terminal-based personal assistant. You run `palico`, it shows your projects sorted by urgency, you pick one, it shows your notes and 1-2 AI suggestions. You chat naturally to log notes and update deadlines — all persisted locally in SQLite.

---

## Stack

| Layer     | Choice                                    |
|-----------|-------------------------------------------|
| Language  | Python 3.11+                              |
| AI        | Gemini API (`google-generativeai`)        |
| Storage   | SQLite (`~/.palico/palico.db`)            |
| Display   | `rich` (tables, panels, styled text)      |
| Packaging | `pyproject.toml` → `palico` shell command |

---

## User Workflow

```
$ palico

  Good morning, luigi.

  Your projects:
  1. palico-cli          due Thu Mar 26  ⚠
  2. portfolio redesign  no deadline
  3. ML side project     due Apr 5

  Which project do you want to tackle?

> palico cli

  ┌─ palico-cli ───────────────────────────────────────────┐
  │  Notes:                                                │
  │  • build REPL loop with persistent Gemini session      │
  │  • use Rich for display                                │
  │  • deploy as pip-installable package                   │
  │                                                        │
  │  Suggestions:                                          │
  │  1. Deadline is Thursday — prioritize core REPL + DB   │
  │     before polishing display.                          │
  │  2. Write a smoke test for the DB layer early to       │
  │     catch schema bugs before they compound.            │
  └────────────────────────────────────────────────────────┘

  You're now focused on palico-cli. Chat away.

> oh btw make sure i finish this by next friday not thursday
  palico: Got it! Updated palico-cli deadline to Fri Mar 27.

> add a note: decided to use click for arg parsing
  palico: Added to palico-cli notes.
```

---

## Data Model (`~/.palico/palico.db`)

```sql
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    description TEXT,
    deadline    DATE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Config lives at `~/.palico/config.json`:
```json
{ "gemini_api_key": "..." }
```
Prompted on first run if missing.

---

## Gemini Integration

### Intent Parsing (every user message)

System prompt:
```
You are palico, a personal project assistant in the terminal.
Today's date is {today}.
Focused project: "{name}" (deadline: {deadline or "none"}).
Notes: {notes}

When the user says something to persist, respond ONLY with JSON:
{
  "action": "add_note" | "set_deadline" | "create_project" | "switch_project" | "none",
  "data": { ... },
  "reply": "..."
}

add_note:       data = { "content": "..." }
set_deadline:   data = { "date": "YYYY-MM-DD" }
create_project: data = { "name": "...", "description": "..." }
switch_project: data = { "name_hint": "..." }
none:           data = {}

Resolve relative dates against today. Return only valid JSON.
```

### Suggestions (on project focus)

One-shot call when user focuses a project:
```
Given notes on "{name}" (deadline: {deadline}):
{notes}

Give exactly 1-2 short, actionable suggestions. Return as a JSON array of strings.
```

---

## Module Structure

```
palico-cli/
├── palico/
│   ├── __init__.py    # empty package marker
│   ├── main.py        # REPL loop, action dispatch, config loading
│   ├── db.py          # SQLite init + all CRUD
│   ├── gemini.py      # Gemini API: parse_intent(), get_suggestions()
│   └── display.py     # Rich: show_dashboard(), show_project(), print_reply()
├── PLAN.md            # this file
├── pyproject.toml     # packaging, entry point
└── README.md
```

### db.py — public interface

```python
def init() -> None                              # create DB + tables if not exist
def get_all_projects() -> list[dict]            # sorted by deadline (nulls last)
def get_project(id: int) -> dict | None
def fuzzy_find_project(hint: str) -> dict | None  # case-insensitive substring match
def create_project(name: str, description: str = "") -> dict
def update_project(id: int, **kwargs) -> None   # name, description, deadline
def add_note(project_id: int, content: str) -> None
def get_notes(project_id: int) -> list[dict]
```

### gemini.py — public interface

```python
def init(api_key: str) -> None
def parse_intent(user_message: str, focused_project: dict | None) -> dict
    # returns: { "action": str, "data": dict, "reply": str }
def get_suggestions(project: dict, notes: list[dict]) -> list[str]
    # returns: list of 1-2 suggestion strings
```

### display.py — public interface

```python
def show_dashboard(projects: list[dict]) -> None
def show_project(project: dict, notes: list[dict], suggestions: list[str]) -> None
def print_reply(text: str) -> None
def prompt_api_key() -> str
```

---

## 3-Terminal Implementation Split

| Terminal | Files | Notes |
|----------|-------|-------|
| T1 | `pyproject.toml`, `palico/__init__.py`, `palico/db.py`, `palico/main.py` | Writes foundation first (stub main.py), wires REPL last |
| T2 | `palico/gemini.py` | Independent — only needs the interfaces above |
| T3 | `palico/display.py` | Independent — only needs the interfaces above |

T2 and T3 run fully in parallel with T1 after foundation files exist. T1 wires `main.py` after T2 and T3 finish.

---

## Verification Checklist

1. `pip install -e .` → `palico` available on PATH
2. Cold run (no `~/.palico/`) → prompted for API key, `~/.palico/` created
3. "start a new project called test app" → project row in DB
4. "make it due next friday" → `sqlite3 ~/.palico/palico.db "select deadline from projects"` shows date
5. "add a note: write unit tests first" → note row in DB
6. `exit` and re-run → dashboard shows "test app" with deadline and urgency indicator
7. Focus "test app" → notes list + suggestions panel rendered
