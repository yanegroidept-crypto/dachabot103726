"""
Работа с краткой историей последних сообщений в чате.

Хранится в state/chat_history.json как список объектов:
{"date": "2026-07-08", "author": "Васильевна", "summary": "..."}

Хранится не более MAX_ITEMS последних записей.
"""

import json
from pathlib import Path

HISTORY_PATH = Path(__file__).resolve().parent.parent / "state" / "chat_history.json"
MAX_ITEMS = 10


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    raw = HISTORY_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    return json.loads(raw)


def append_history(author: str, summary: str, date: str) -> None:
    history = load_history()
    history.append({"date": date, "author": author, "summary": summary})
    history = history[-MAX_ITEMS:]
    HISTORY_PATH.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def history_as_text() -> str:
    history = load_history()
    if not history:
        return "История пуста, это одно из первых сообщений в чате."
    lines = [f"- {h['date']} {h['author']}: {h['summary']}" for h in history]
    return "\n".join(lines)
