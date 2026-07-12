"""
Вечерний пост Васильевны в ветку "Общий чат".
Запускается по расписанию в 21:45.

Логика полностью аналогична утреннему посту (post_morning.py),
но использует другой пример стиля и другой смысловой фокус
(подведение итога дня + подробный прогноз на завтра, с кратким
упоминанием прогноза до конца недели).
"""

import datetime
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from weather import get_evening_forecast_summary
from history import history_as_text, append_history
from run_safely import run_safely

BASE_DIR = Path(__file__).resolve().parent.parent


def build_prompt() -> str:
    character = (BASE_DIR / "characters" / "vasilevna.md").read_text(encoding="utf-8")
    example = (BASE_DIR / "examples" / "vasilevna_evening.md").read_text(encoding="utf-8")
    weather = get_evening_forecast_summary()
    history = history_as_text()

    return f"""Ты — бот-персонаж в дачном Telegram-чате садового товарищества.
Вот описание твоего стиля и характера:

{character}

Вот пример твоего вечернего поста (используй только как образец СТИЛЯ,
не копируй текст дословно, содержание должно быть новым):

{example}

Прогноз погоды (используй эти данные, не выдумывай другие цифры):
{weather}

Основной акцент поста — подробный прогноз на ЗАВТРА (первая строка выше).
Остальные дни до конца недели (если приведены) упомяни коротко, одной
фразой в конце поста — не расписывай подробно каждый день. ВАЖНО: используй
только те дни, которые реально присутствуют в данных выше — если прогноз
покрывает не всю неделю (например только 2-3 дня), НЕ придумывай погоду на
дни, для которых данных нет, и не упоминай их вообще.

История последних сообщений в чате (учитывай контекст для естественности,
но НЕ зацикливайся на ней — упоминай только если реально уместно,
например если несколько дней подряд лила погода, а теперь наконец
распогодилось — это стоит подчеркнуть с облегчением; в остальных
случаях просто имей контекст в виду, не педалируй):

{history}

Напиши вечерний пост в общий чат СТ — короткое подведение дня и подробно
что ждать завтра по погоде, плюс одну короткую фразу о том, что ждёт до
конца недели.
Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "текст поста для отправки в telegram, с эмодзи по стилю персонажа", "history_summary": "одна короткая фраза для истории чата, например: 'Васильевна написала вечерний пост, завтра обещали дождь'"}}
"""


def main() -> None:
    prompt = build_prompt()
    raw_response = generate(prompt)
    post_text, summary = safe_parse_post_response(
        raw_response, default_summary="Васильевна написала вечерний пост"
    )

    send_message("TG_BOT_TOKEN_VASILEVNA", "TOPIC_ID_GENERAL", post_text)

    today = datetime.date.today().isoformat()
    append_history("Васильевна", summary, today)

    print("Вечерний пост Васильевны отправлен успешно.")


if __name__ == "__main__":
    run_safely(main, label="Вечерний пост Васильевны")
