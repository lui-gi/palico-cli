import sqlite3
from pathlib import Path
from datetime import date

DB_DIR = Path.home() / ".palico"
DB_PATH = DB_DIR / "palico.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _row_to_dict(row) -> dict:
    return dict(row) if row else None


def init() -> None:
    DB_DIR.mkdir(exist_ok=True)
    with _connect() as conn:
        conn.executescript("""
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
        """)


def get_all_projects() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT * FROM projects
            ORDER BY
                CASE WHEN deadline IS NULL THEN 1 ELSE 0 END,
                deadline ASC
        """).fetchall()
    return [dict(r) for r in rows]


def get_project(id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
    return _row_to_dict(row)


def fuzzy_find_project(hint: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE LOWER(name) LIKE ?",
            (f"%{hint.lower()}%",),
        ).fetchone()
    return _row_to_dict(row)


def create_project(name: str, description: str = "") -> dict:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def update_project(id: int, **kwargs) -> None:
    allowed = {"name", "description", "deadline"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = date.today().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [id]
    with _connect() as conn:
        conn.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
        conn.commit()


def add_note(project_id: int, content: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO notes (project_id, content) VALUES (?, ?)",
            (project_id, content),
        )
        conn.commit()


def get_notes(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE project_id = ? ORDER BY created_at ASC",
            (project_id,),
        ).fetchall()
    return [dict(r) for r in rows]
