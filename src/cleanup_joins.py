"""
Скрипт для удаления сервисных сообщений о вступлении новых участников в чат.
Использует API getUpdates для поиска таких сообщений и deleteMessage для их удаления.
"""

import os
import requests
from run_safely import run_safely
from telegram_client import delete_message, _get_token

def cleanup_joins() -> None:
    token = _get_token("TG_BOT_TOKEN_VASILEVNA")
    base_url = f"https://api.telegram.org/bot{token}"
    
    # Получаем обновления
    try:
        response = requests.get(f"{base_url}/getUpdates", timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Ошибка при получении обновлений: {e}")
        return

    updates = data.get("result", [])
    if not updates:
        return

    last_update_id = 0
    deleted_count = 0

    for update in updates:
        last_update_id = max(last_update_id, update["update_id"])
        
        message = update.get("message")
        if not message:
            continue
            
        # Проверяем, есть ли поле new_chat_members
        if "new_chat_members" in message:
            msg_id = message["message_id"]
            chat_id = message["chat"]["id"]
            
            # Проверяем, что это наш чат (на всякий случай)
            target_chat_id = os.environ.get("TG_CHAT_ID")
            if str(chat_id) == str(target_chat_id):
                if delete_message("TG_BOT_TOKEN_VASILEVNA", msg_id):
                    deleted_count += 1
                    print(f"Удалено сообщение о вступлении: {msg_id}")

    # Подтверждаем получение обновлений, чтобы они не приходили в следующий раз
    if last_update_id > 0:
        requests.get(f"{base_url}/getUpdates", params={"offset": last_update_id + 1}, timeout=10)

    if deleted_count > 0:
        print(f"Всего удалено сообщений: {deleted_count}")

if __name__ == "__main__":
    run_safely(cleanup_joins, label="Очистка сообщений о вступлении")
