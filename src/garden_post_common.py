"""
Общая логика для поста в тематический топик (используется всеми
персонажами, у которых в стеке лежит готовый ready_post: Васильевна,
Петрович, Оля, Эдик):
1. Берёт следующую тему из стека персонажа (topics_stack.py).
2. Готовый текст поста (ready_post) слегка адаптирует под стиль
   персонажа, историю чата и текущий контекст через Gemini —
   либо, если хотите публиковать 1-в-1 без Gemini, можно отправлять
   ready_post напрямую (см. флаг USE_GEMINI_ADAPTATION ниже).
3. Отправляет в указанный топик (параметр topic_id_env).
4. Обновляет историю чата.

Функция garden_post() параметризована именем персонажа и топиком,
поэтому post_garden_vasilevna.py, post_garden_petrovich.py,
post_garden_olya.py и post_garden_edik.py — это тонкие обёртки над ней.
"""

import datetime
import os
from pathlib import Path

from gemini_client import generate, safe_parse_post_response
from telegram_client import send_message
from history import history_as_text, append_history
from topics_stack import get_next_topic

BASE_DIR = Path(__file__).resolve().parent.parent


def _resolve_use_gemini_adaptation(character_key: str, default: bool) -> bool:
    """
    Решает, нужно ли гнать готовый ready_post через Gemini для лёгкой
    адаптации (стиль, учёт истории), или публиковать как есть.

    По умолчанию берётся `default`, переданный вызывающим скриптом
    (post_garden_<character>.py) — так у каждого персонажа свой
    базовый режим (например, True для Петровича/Васильевны, False для
    Оли/Эдика).

    Это можно переопределить без деплоя нового кода через переменные
    окружения:
    - USE_GEMINI_ADAPTATION_<CHARACTER_KEY> (приоритет, персонально для
      одного персонажа, например USE_GEMINI_ADAPTATION_OLYA=true)
    - USE_GEMINI_ADAPTATION (общий флаг на всех, если персональный не
      задан) — например, если все 10 ключей Gemini исчерпали лимит и
      нужно временно отключить адаптацию везде разом.
    """
    personal_env = f"USE_GEMINI_ADAPTATION_{character_key.upper()}"
    if personal_env in os.environ:
        return os.environ[personal_env].strip().lower() not in ("false", "0", "no")
    if "USE_GEMINI_ADAPTATION" in os.environ:
        return os.environ["USE_GEMINI_ADAPTATION"].strip().lower() not in ("false", "0", "no")
    return default


def garden_post(
    character_key: str,
    character_display_name: str,
    stack_filename: str,
    bot_token_env: str,
    topic_id_env: str = "TOPIC_ID_GARDEN",
    use_gemini_adaptation: bool = True,
) -> None:
    character = (BASE_DIR / "characters" / f"{character_key}.md").read_text(encoding="utf-8")
    topic = get_next_topic(stack_filename)
    history = history_as_text()

    if _resolve_use_gemini_adaptation(character_key, use_gemini_adaptation):
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

    send_message(bot_token_env, topic_id_env, post_text, disable_notification=True)

    today = datetime.date.today().isoformat()
    append_history(character_display_name, summary, today)

    print(f"Пост {character_display_name} в топик {topic_id_env} отправлен ({topic['id']}).")
