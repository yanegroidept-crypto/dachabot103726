"""
Общая логика для поста в ветку "Дача, сад, огород":
1. Берёт следующую тему из стека персонажа (topics_stack.py).
2. Готовый текст поста (ready_post) слегка адаптирует под стиль
   персонажа, историю чата и текущий контекст через Gemini —
   либо, если хотите публиковать 1-в-1 без Gemini, можно отправлять
   ready_post напрямую (см. флаг USE_GEMINI_ADAPTATION ниже).
3. Отправляет в топик "Дача, сад, огород".
4. Обновляет историю чата.

Функция garden_post() параметризована именем персонажа, поэтому
post_garden_vasilevna.py и post_garden_petrovich.py — это тонкие
обёртки над ней.
"""

import datetime
import os
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from history import history_as_text, append_history
from topics_stack import get_next_topic

BASE_DIR = Path(__file__).resolve().parent.parent

# Если True — готовый пост из стека пропускается через Gemini для лёгкой
# адаптации (стиль, учёт истории). Если False — публикуется как есть,
# без вызова Gemini (экономит запросы, но менее гибко).
# Можно переопределить переменной окружения USE_GEMINI_ADAPTATION=false —
# без деплоя нового кода, например если все 10 ключей исчерпали лимит.
USE_GEMINI_ADAPTATION = os.environ.get("USE_GEMINI_ADAPTATION", "true").strip().lower() not in (
    "false", "0", "no",
)


def garden_post(
    character_key: str,
    character_display_name: str,
    stack_filename: str,
    bot_token_env: str,
) -> None:
    character = (BASE_DIR / "characters" / f"{character_key}.md").read_text(encoding="utf-8")
    topic = get_next_topic(stack_filename)
    history = history_as_text()

    if USE_GEMINI_ADAPTATION:
        prompt = f"""Ты — бот-персонаж в дачном Telegram-чате садового товарищества.
Вот описание твоего стиля и характера:

{character}

Вот готовая заготовка поста на сегодняшнюю тему "{topic['topic']}":

{topic['ready_post']}

СТРОГИЕ ПРАВИЛА АДАПТАЦИИ (соблюдай все пункты одновременно):
1. Сохрани ВСЕ эмодзи из заготовки ровно на тех же местах, где они стоят
   (не убирай их и не добавляй новые), даже если описание стиля персонажа
   говорит об умеренном использовании эмодзи — заготовка уже учитывает стиль.
2. Сохрани структуру блоков и заголовков из заготовки (порядок и состав
   разделов не менять).
3. Можно только слегка перефразировать формулировки внутри блоков под
   манеру речи персонажа (обращения, характерные словечки, порядок слов).
4. НЕ меняй фактическое содержание совета.
5. НЕ добавляй факты, детали или реплики, которых нет в заготовке или в
   описании персонажа выше — ничего от себя, даже в качестве "живого"
   зачина или отсылок к истории чата.
6. Историю чата ниже используй ТОЛЬКО чтобы не повторяться в приветствии
   дословно как в прошлый раз — не пересказывай и не комментируй события
   из истории.

История последних сообщений в чате (только для контроля повторов, см. правило 6):

{history}

Ответь СТРОГО в формате JSON, без markdown-разметки и без пояснений:
{{"post_text": "финальный текст поста для telegram (эмодзи и структура — как в заготовке, см. правила выше)", "history_summary": "одна короткая фраза для истории чата, например: '{character_display_name} написала пост про крапиву'"}}
"""
        raw_response = generate(prompt)
        default_summary = f"{character_display_name} написал(а) пост про: {topic['topic']}"
        post_text, summary = safe_parse_post_response(raw_response, default_summary)
    else:
        post_text = topic["ready_post"]
        summary = f"{character_display_name} написал(а) пост про: {topic['topic']}"

    send_message(bot_token_env, "TOPIC_ID_GARDEN", post_text, disable_notification=True)

    today = datetime.date.today().isoformat()
    append_history(character_display_name, summary, today)

    print(f"Пост {character_display_name} в 'Дача, сад, огород' отправлен ({topic['id']}).")
