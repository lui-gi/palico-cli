from __future__ import annotations

import json
from pathlib import Path


def sessions_dir() -> Path:
    d = Path.home() / ".palico" / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load(name: str) -> list[dict]:
    path = sessions_dir() / f"{name}.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("history", [])
    except (json.JSONDecodeError, KeyError):
        return []


def save(name: str, history: list[dict]) -> None:
    path = sessions_dir() / f"{name}.json"
    path.write_text(json.dumps({"session": name, "history": history}, indent=2))


def list_sessions() -> list[str]:
    return sorted(p.stem for p in sessions_dir().glob("*.json"))


def clear(name: str) -> None:
    path = sessions_dir() / f"{name}.json"
    if path.exists():
        path.unlink()
