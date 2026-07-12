"""
Выбор случайной ещё не использованной картинки из humor/<character>/
для поста в тему "Дачный юмор".

Отслеживает уже показанные картинки в state/used_humor.json,
чтобы не повторяться, пока не покажет все — тогда список для
этого персонажа сбрасывается.
"""

import json
import random
from pathlib import Path

HUMOR_DIR = Path(__file__).resolve().parent.parent / "humor"
USED_HUMOR_PATH = Path(__file__).resolve().parent.parent / "state" / "used_humor.json"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _load_used() -> dict:
    if not USED_HUMOR_PATH.exists():
        return {}
    raw = USED_HUMOR_PATH.read_text(encoding="utf-8").strip()
    return json.loads(raw) if raw else {}


def _save_used(data: dict) -> None:
    USED_HUMOR_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _list_images(character_key: str) -> list[str]:
    folder = HUMOR_DIR / character_key
    if not folder.exists():
        return []
    return sorted(
        f.name for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def get_next_image(character_key: str) -> str | None:
    """
    Возвращает путь к следующей неиспользованной картинке для персонажа
    (например "vasilevna", "petrovich", "edik"), помечает её как использованную.
    Возвращает None, если в папке вообще нет картинок.
    """
    all_images = _list_images(character_key)
    if not all_images:
        return None

    used_data = _load_used()
    used_for_character = set(used_data.get(character_key, []))

    unused = [img for img in all_images if img not in used_for_character]
    if not unused:
        # все показаны — начинаем заново
        unused = all_images
        used_for_character = set()

    chosen = random.choice(unused)
    used_for_character.add(chosen)
    used_data[character_key] = sorted(used_for_character)
    _save_used(used_data)

    return str(HUMOR_DIR / character_key / chosen)
