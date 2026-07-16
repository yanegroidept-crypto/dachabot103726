"""
Пост Оли в её СОБСТВЕННЫЙ топик (TOPIC_ID_OLYA) — отдельный от
"Дача, сад, огород" (TOPIC_ID_GARDEN), где постят Васильевна и Петрович.

Как и у Петровича/Васильевны, в стеке topics_stack/olya_garden.json
теперь лежит ГОТОВЫЙ текст поста (ready_post), написанный заранее
вручную — Gemini здесь ничего не генерирует с нуля, только (опционально,
см. USE_GEMINI_ADAPTATION в garden_post_common.py) слегка адаптирует
готовый текст под стиль и историю чата.

Запускается как часть дневного ротационного цикла (см.
post_daily_rotation.py), но может быть запущен и отдельно.
"""

from garden_post_common import garden_post
from run_safely import run_safely

CHARACTER_KEY = "olya"
CHARACTER_DISPLAY_NAME = "Оля"
STACK_FILENAME = "olya_garden.json"
BOT_TOKEN_ENV = "TG_BOT_TOKEN_OLYA"
TOPIC_ENV = "TOPIC_ID_OLYA"


def main() -> None:
    garden_post(
        character_key=CHARACTER_KEY,
        character_display_name=CHARACTER_DISPLAY_NAME,
        stack_filename=STACK_FILENAME,
        bot_token_env=BOT_TOKEN_ENV,
        topic_id_env=TOPIC_ENV,
        # Публикуем готовый текст 1-в-1, без прогона через Gemini.
        # Переопределить можно через USE_GEMINI_ADAPTATION_OLYA=true
        # или общий USE_GEMINI_ADAPTATION, см. garden_post_common.py.
        use_gemini_adaptation=False,
    )


if __name__ == "__main__":
    run_safely(main, label="Пост Оли в её топик")
