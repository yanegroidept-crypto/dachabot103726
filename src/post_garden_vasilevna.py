"""
Пост Васильевны в ветку "Дача, сад, огород". Запускается в 12:00.
Берёт следующую тему из topics_stack/vasilevna_garden.json.
"""

from garden_post_common import garden_post
from run_safely import run_safely


def main() -> None:
    garden_post(
        character_key="vasilevna",
        character_display_name="Васильевна",
        stack_filename="vasilevna_garden.json",
        bot_token_env="TG_BOT_TOKEN_VASILEVNA",
    )


if __name__ == "__main__":
    run_safely(main, label="Пост Васильевны в 'Дача, сад, огород'")
