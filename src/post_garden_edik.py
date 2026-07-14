"""
Пост Эдика в его СОБСТВЕННЫЙ топик (TOPIC_ID_EDIK) — отдельный от
"Дача, сад, огород" (TOPIC_ID_GARDEN), где постят Васильевна и Петрович.

В отличие от post_garden_petrovich.py / post_garden_vasilevna.py, в
стеке topics_stack/edik_garden.json лежат ТОЛЬКО темы (без готового
текста ready_post) — сам пост с нуля генерирует Gemini по описанию
характера Эдика (characters/edik.md) и образцу стиля
(examples/edik_garden.md), опираясь на выбранную тему.

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

CHARACTER_KEY = "edik"
CHARACTER_DISPLAY_NAME = "Эдик"
STACK_FILENAME = "edik_garden.json"
BOT_TOKEN_ENV = "TG_BOT_TOKEN_EDIK"
TOPIC_ENV = "TOPIC_ID_EDIK"


def build_prompt(topic: str, character: str, example: str, history: str) -> str:
    return f"""Ты — бот-персонаж в Telegram-чате для мужчин.
Вот описание твоего стиля и характера:

{character}

Вот пример твоего поста в свой топик по своей теме
(используй только как образец СТИЛЯ, структуры и манеры речи, не копируй
текст дословно):

{example}

Напиши СЕГОДНЯШНИЙ пост в свой топик на тему:
"{topic}"

Требования:
1. ПИШИ КОНКРЕТНО ПО ТЕМЕ!! Не как айтишник про технологии, а как мужик про мужскую тему. Имено как мужик мужику
2. Не повторяй дословно вступление или шутки из истории последних постов
   ниже — если про очки или похожий зачин уже шутили недавно, обыграй
   иначе.
3. Не критикуй Петровича или других родственников напрямую, оставайся
   дружелюбным и уважительным.
4. Не говори постоянно "как мужик мужику"
5. Не используй символы для выделения слов типа "**" или другие
6. Пост длинный, ровно 250 слов, +/- 5
7. Не пиши каждый раз "Всем коннект!"
8. Обязательно вставляй смайлики. пару штук в посте: 5-7
9. Пост должен быть написан полностью самостоятельно на заданную тему —
   готового текста для этой темы не существует, придумай содержание сам,
   в характере и манере Эдика (IT-сленг, структура со списком, призыв ставить «+» в комментариях,
   хэштеги в конце — как в примере).

История последних сообщений в чате (только для контроля повторов, см. пункт 2):

{history}

Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "финальный текст поста для telegram, с эмодзи и структурой в стиле Эдика", "history_summary": "одна короткая фраза для истории чата, например: 'Эдик написал пост про умный полив'"}}
"""


def main() -> None:
    character = (BASE_DIR / "characters" / f"{CHARACTER_KEY}.md").read_text(encoding="utf-8")
    example = (BASE_DIR / "examples" / "edik_garden.md").read_text(encoding="utf-8")
    topic = get_next_topic(STACK_FILENAME)
    history = history_as_text()

    prompt = build_prompt(topic["topic"], character, example, history)
    raw_response = generate(prompt)
    default_summary = f"{CHARACTER_DISPLAY_NAME} написал пост про: {topic['topic']}"
    post_text, summary = safe_parse_post_response(raw_response, default_summary)

    send_message(BOT_TOKEN_ENV, TOPIC_ENV, post_text, disable_notification=True)

    today = datetime.date.today().isoformat()
    append_history(CHARACTER_DISPLAY_NAME, summary, today)

    print(f"Пост {CHARACTER_DISPLAY_NAME} в его топик отправлен ({topic['id']}).")


if __name__ == "__main__":
    run_safely(main, label="Пост Эдика в его топик")
