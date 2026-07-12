"""
Отправка сообщений/фото от имени конкретного бота в конкретный
топик (тему) супергруппы Telegram.

bot_token_env — имя переменной окружения с токеном нужного бота
                (например "TG_BOT_TOKEN_VASILEVNA")
topic_env     — имя переменной окружения с id топика
                (например "TOPIC_ID_GENERAL")
"""

import os

import requests


def _get_token(bot_token_env: str) -> str:
    token = os.environ.get(bot_token_env)
    if not token:
        raise RuntimeError(f"Не найден токен бота в переменной {bot_token_env}")
    return token


def _get_thread_id(topic_env: str) -> int:
    value = os.environ.get(topic_env)
    if not value:
        raise RuntimeError(f"Не найден id топика в переменной {topic_env}")
    return int(value)


def send_message(
    bot_token_env: str,
    topic_env: str,
    text: str,
    disable_notification: bool = True,
) -> dict:
    token = _get_token(bot_token_env)
    chat_id = os.environ["TG_CHAT_ID"]
    thread_id = _get_thread_id(topic_env)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "message_thread_id": thread_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": disable_notification,
    }
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


def delete_message(
    bot_token_env: str,
    message_id: int,
) -> bool:
    token = _get_token(bot_token_env)
    chat_id = os.environ["TG_CHAT_ID"]

    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
    }
    response = requests.post(url, json=payload, timeout=15)
    # Если сообщение уже удалено или не существует, Telegram может вернуть 400.
    # Для целей чистки нам это не критично, поэтому просто возвращаем статус успеха.
    return response.ok


def send_photo(
    bot_token_env: str,
    topic_env: str,
    photo_path: str,
    caption: str = "",
    disable_notification: bool = True,
) -> dict:
    token = _get_token(bot_token_env)
    chat_id = os.environ["TG_CHAT_ID"]
    thread_id = _get_thread_id(topic_env)

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(photo_path, "rb") as photo_file:
        files = {"photo": photo_file}
        data = {
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "caption": caption,
            "disable_notification": disable_notification,
        }
        response = requests.post(url, data=data, files=files, timeout=30)
    response.raise_for_status()
    return response.json()
