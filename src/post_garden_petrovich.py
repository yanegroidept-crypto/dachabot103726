"""
Пост Петровича в ветку "Дача, сад, огород". Запускается в 17:00.
Берёт следующую тему из topics_stack/petrovich_garden.json.
"""

from garden_post_common import garden_post
from run_safely import run_safely


def main() -> None:
    garden_post(
        character_key="petrovich",
        character_display_name="Петрович",
        stack_filename="petrovich_garden.json",
        bot_token_env="TG_BOT_TOKEN_PETROVICH",
    )


if __name__ == "__main__":
    run_safely(main, label="Пост Петровича в 'Дача, сад, огород'")
