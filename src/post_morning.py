"""
Утренний пост Васильевны в ветку "Общий чат".
Запускается по расписанию в 08:30.

Логика:
1. Берёт стиль персонажа + пример утреннего поста.
2. Запрашивает прогноз погоды на сегодня по координатам СТ.
3. Учитывает последние 10 событий из истории чата.
4. Просит Gemini сгенерировать пост + краткое summary для истории.
5. Отправляет пост в Telegram, обновляет историю.
"""

import datetime
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from weather import get_today_forecast_summary
from history import history_as_text, append_history
from run_safely import run_safely

BASE_DIR = Path(__file__).resolve().parent.parent


def build_prompt() -> str:
    character = (BASE_DIR / "characters" / "vasilevna.md").read_text(encoding="utf-8")
    example = (BASE_DIR / "examples" / "vasilevna_morning.md").read_text(encoding="utf-8")
    weather = get_today_forecast_summary()
    history = history_as_text()

    return f"""Ты — бот-персонаж в дачном Telegram-чате садового товарищества.
Вот описание твоего стиля и характера:

{character}

Вот пример твоего утреннего поста (используй только как образец СТИЛЯ,
не копируй текст дословно, содержание должно быть новым):

{example}

Прогноз погоды на сегодня (используй эти данные, не выдумывай другие):
{weather}

История последних сообщений в чате (учитывай контекст для естественности,
но НЕ зацикливайся на ней и не упоминай её в каждом посте — только если
это реально уместно, например если много дней подряд была плохая погода
и наконец-то распогодилось):

{history}

Напиши утренний пост в общий чат СТ на основе сегодняшней погоды.
Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "текст поста для отправки в telegram, с эмодзи по стилю персонажа", "history_summary": "одна короткая фраза для истории чата, например: 'Васильевна написала утренний пост, погода солнечная +18'"}}
"""


def main() -> None:
    prompt = build_prompt()
    raw_response = generate(prompt)
    post_text, summary = safe_parse_post_response(
        raw_response, default_summary="Васильевна написала утренний пост"
    )

    send_message("TG_BOT_TOKEN_VASILEVNA", "TOPIC_ID_GENERAL", post_text)

    today = datetime.date.today().isoformat()
    append_history("Васильевна", summary, today)

    print("Утренний пост Васильевны отправлен успешно.")


if __name__ == "__main__":
    run_safely(main, label="Утренний пост Васильевны")
