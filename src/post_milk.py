"""
Пост Оли в ветку "Молочная продукция". Запускается по средам и субботам
в 09:30, сообщает что в 10:00 приедут молочники.

Этот пост по смыслу шаблонный и не требует истории чата — но для
живости всё равно прогоняется через Gemini с примером стиля, чтобы
формулировки не повторялись день в день дословно.
"""

import datetime
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from history import append_history
from run_safely import run_safely

BASE_DIR = Path(__file__).resolve().parent.parent


def build_prompt() -> str:
    character = (BASE_DIR / "characters" / "olya.md").read_text(encoding="utf-8")
    example = (BASE_DIR / "examples" / "olya_milk.md").read_text(encoding="utf-8")

    return f"""Ты — бот-персонаж в дачном Telegram-чате садового товарищества.
Вот описание твоего стиля и характера:

{character}

Вот пример твоего поста про молочников (используй только как образец
СТИЛЯ, не копируй текст дословно):

{example}

Напиши сегодняшний пост в ветку "Молочная продукция": напомни, что
сегодня в 10:00 приедут молочники, место встречи — как обычно
(у шлагбаума). Пост должен быть коротким, информативным, дружелюбным.

Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "текст поста для telegram, с эмодзи по стилю персонажа", "history_summary": "одна короткая фраза для истории чата, например: 'Оля напомнила про молочников в 10:00'"}}
"""


def main() -> None:
    prompt = build_prompt()
    raw_response = generate(prompt)
    post_text, summary = safe_parse_post_response(
        raw_response, default_summary="Оля напомнила про молочников"
    )

    send_message("TG_BOT_TOKEN_OLYA", "TOPIC_ID_MILK", post_text)

    today = datetime.date.today().isoformat()
    append_history("Оля", summary, today)

    print("Пост Оли про молочников отправлен успешно.")


if __name__ == "__main__":
    run_safely(main, label="Пост Оли про молочников")
