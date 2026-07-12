"""
Работа со стеком готовых тем/постов (topics_stack/*.json).

Логика: берём первый элемент с used=false, используем его
ready_post (при желании — пропускаем через Gemini для лёгкой
адаптации под погоду/историю), помечаем used=true и сохраняем.

Когда все темы использованы — стек автоматически перезапускается
(все used сбрасываются в false), чтобы бот не остался без тем.
"""

import json
from pathlib import Path

STACK_DIR = Path(__file__).resolve().parent.parent / "topics_stack"


def _stack_path(filename: str) -> Path:
    return STACK_DIR / filename


def load_stack(filename: str) -> list[dict]:
    path = _stack_path(filename)
    return json.loads(path.read_text(encoding="utf-8"))


def save_stack(filename: str, stack: list[dict]) -> None:
    path = _stack_path(filename)
    path.write_text(json.dumps(stack, ensure_ascii=False, indent=2), encoding="utf-8")


def get_next_topic(filename: str) -> dict:
    """
    Возвращает следующую неиспользованную тему и помечает её used=true.
    Если все темы использованы — сбрасывает весь стек и начинает заново.
    """
    stack = load_stack(filename)
    if not stack:
        raise RuntimeError(
            f"Стек тем {filename} пуст — добавьте хотя бы одну тему, иначе постить нечего."
        )

    unused = [item for item in stack if not item.get("used", False)]
    if not unused:
        for item in stack:
            item["used"] = False
        unused = stack

    chosen = unused[0]
    for item in stack:
        if item["id"] == chosen["id"]:
            item["used"] = True
            break

    save_stack(filename, stack)
    return chosen
