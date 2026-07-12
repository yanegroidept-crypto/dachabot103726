"""
Пост "Дачный юмор" в 19:00. Три бота (Васильевна, Петрович, Эдик)
по очереди кидают картинку из своей подпапки humor/<character>/.

Специально сделано ОДНИМ скриптом (не тремя отдельными workflow),
чтобы не было гонки при коммите state/used_humor.json — если бы
три параллельных job пытались одновременно закоммитить изменения
в один и тот же файл, это привело бы к конфликтам git push.
"""

from telegram_client import send_photo
from humor_picker import get_next_image
from run_safely import run_safely

# character_key, bot_token_env
CHARACTERS = [
    ("vasilevna", "TG_BOT_TOKEN_VASILEVNA"),
    ("petrovich", "TG_BOT_TOKEN_PETROVICH"),
    ("edik", "TG_BOT_TOKEN_EDIK"),
]


def main() -> None:
    errors = []
    for character_key, bot_token_env in CHARACTERS:
        try:
            image_path = get_next_image(character_key)
            if image_path is None:
                print(f"[!] Нет картинок в humor/{character_key}/, пропускаю.")
                continue

            send_photo(bot_token_env, "TOPIC_ID_HUMOR", image_path)
            print(f"Картинка от {character_key} отправлена: {image_path}")
        except Exception as exc:
            err_msg = f"Ошибка отправки юмора от {character_key}: {exc}"
            print(f"[!] {err_msg}")
            errors.append(err_msg)

    if errors:
        raise RuntimeError(" | ".join(errors))


if __name__ == "__main__":
    run_safely(main, label="Пост 'Дачный юмор'")
