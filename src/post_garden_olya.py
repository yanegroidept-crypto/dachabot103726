"""
Пост Оли в её СОБСТВЕННЫЙ топик (TOPIC_ID_OLYA) — отдельный от
"Дача, сад, огород" (TOPIC_ID_GARDEN), где постят Васильевна и Петрович.

Как и post_garden_edik.py, в стеке topics_stack/olya_garden.json лежат
ТОЛЬКО темы (без готового текста ready_post) — сам пост с нуля
генерирует Gemini по описанию характера Оли (characters/olya.md) и
образцу стиля (examples/olya_garden.md), опираясь на выбранную тему.

Запускается как часть дневного ротационного цикла (см.
post_daily_rotation.py), но может быть запущен и отдельно.
"""

import datetime
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from history import history_as_text, append_history
from topics_stack import get_next_topic
from run_safely import run_safely

BASE_DIR = Path(__file__).resolve().parent.parent

CHARACTER_KEY = "olya"
CHARACTER_DISPLAY_NAME = "Оля"
STACK_FILENAME = "olya_garden.json"
BOT_TOKEN_ENV = "TG_BOT_TOKEN_OLYA"
TOPIC_ENV = "TOPIC_ID_OLYA"


def build_prompt(topic: str, character: str, example: str, history: str) -> str:
    return f"""Ты — бот-персонаж в дачном Telegram-чате садового товарищества.
Вот описание твоего стиля и характера:

{character}

Вот пример твоего поста в свой топик по своей теме (используй только
как образец СТИЛЯ, структуры и манеры речи, не копируй текст дословно):

{example}

Напиши СЕГОДНЯШНИЙ пост в свой топик на тему:
"{topic}"

Требования:
1. ПИШИ КОНКРЕТНО ПО ТЕМЕ!! Раскрывай именно заявленную тему, а не общие
   рассуждения об эстетике вообще.
2. Не повторяй дословно вступление или шутки из истории последних постов
   ниже — если похожий приём (например "ожидание/реальность") уже был
   совсем недавно, обыграй иначе.
3. Не критикуй маму (Васильевну) и отца (Петровича) напрямую — только с
   доброй, любящей иронией, как указано в характере.
4. Не используй символы для выделения слов типа "**" или другую
   markdown-разметку.
5. Пост длиной примерно 150-200 слов.
6. Обязательно вставляй смайлики в стиле персонажа (🌿, ✨, ☕, 🕊️, 🧺) —
   пару штук по тексту, без перебора.
7. Структура аккуратная, можно с коротким списком, где уместно.
8. Пост должен быть написан полностью самостоятельно на заданную тему —
   готового текста для этой темы не существует, придумай содержание сам,
   в характере и манере Оли (эстетика, лёгкая ирония про суровые дачные
   реалии, обращения вроде "девочки", "дорогие мои"). В конце — вопрос к
   соседям и 2-3 хэштега, как в примере.

История последних сообщений в чате (только для контроля повторов, см. пункт 2):

{history}

Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "финальный текст поста для telegram, с эмодзи и структурой в стиле Оли", "history_summary": "одна короткая фраза для истории чата, например: 'Оля написала пост про лавандовую зону'"}}
"""


def main() -> None:
    character = (BASE_DIR / "characters" / f"{CHARACTER_KEY}.md").read_text(encoding="utf-8")
    example = (BASE_DIR / "examples" / "olya_garden.md").read_text(encoding="utf-8")
    topic = get_next_topic(STACK_FILENAME)
    history = history_as_text()

    prompt = build_prompt(topic["topic"], character, example, history)
    raw_response = generate(prompt)
    default_summary = f"{CHARACTER_DISPLAY_NAME} написала пост про: {topic['topic']}"
    post_text, summary = safe_parse_post_response(raw_response, default_summary)

    send_message(BOT_TOKEN_ENV, TOPIC_ENV, post_text, disable_notification=True)

    today = datetime.date.today().isoformat()
    append_history(CHARACTER_DISPLAY_NAME, summary, today)

    print(f"Пост {CHARACTER_DISPLAY_NAME} в её топик отправлен ({topic['id']}).")


if __name__ == "__main__":
    run_safely(main, label="Пост Оли в её топик")
