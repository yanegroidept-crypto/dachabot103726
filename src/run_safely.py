"""
Обёртка для main() любого пост-скрипта: ловит любое исключение,
логирует полный traceback, дописывает короткую запись в
state/errors.log (формат "имя_скрипта.py:ТипОшибки: сообщение")
и пытается отправить короткое уведомление об ошибке в личку через
ADMIN_BOT_TOKEN/ADMIN_CHAT_ID (если заданы), чтобы падение поста не
осталось незамеченным до заглядывания в cron-логи.

Использование в каждом post_*.py:

    from run_safely import run_safely

    def main() -> None:
        ...

    if __name__ == "__main__":
        run_safely(main, label="Утренний пост Васильевны")
"""

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Callable

import requests

logger = logging.getLogger(__name__)

ERROR_LOG_PATH = Path(__file__).resolve().parent.parent / "state" / "errors.log"


def _log_error_to_file(exc: Exception) -> None:
    """
    Дописывает в state/errors.log строку вида "post_evening.py:RuntimeError: ...".
    Имя скрипта берётся из sys.argv[0] (тот файл, что был запущен через
    `python post_evening.py`), а не из label — так проще искать по логу
    grep'ом и не зависит от того, как называется label.
    """
    script_name = Path(sys.argv[0]).name
    line = f"{script_name}:{type(exc).__name__}: {exc}\n"
    try:
        ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        logger.exception("Не удалось записать ошибку в %s", ERROR_LOG_PATH)


def _notify_admin(label: str, exc: Exception) -> None:
    token = os.environ.get("ADMIN_BOT_TOKEN")
    chat_id = os.environ.get("ADMIN_CHAT_ID")
    if not token or not chat_id:
        logger.warning(
            "ADMIN_BOT_TOKEN/ADMIN_CHAT_ID не заданы — уведомление об ошибке "
            "не отправлено, смотрите логи."
        )
        return

    text = f"⚠️ {label} не отправился.\n{type(exc).__name__}: {exc}"
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception:  # noqa: BLE001 — уведомление best-effort, не должно маскировать исходную ошибку
        logger.exception("Не удалось отправить уведомление об ошибке администратору")


def _validate_env_variables() -> None:
    """
    Проверяет наличие необходимых переменных окружения перед запуском основного кода.
    Если каких-то обязательных настроек не хватает, выбрасывает ValueError.
    """
    script_name = Path(sys.argv[0]).name
    
    # Общие обязательные переменные
    required = ["TG_CHAT_ID"]
    
    # Переменные по скриптам
    if script_name == "post_morning.py":
        required += ["TG_BOT_TOKEN_VASILEVNA", "TOPIC_ID_GENERAL", "WEATHER_API_KEY", "DACHA_LAT", "DACHA_LON"]
    elif script_name == "post_evening.py":
        required += ["TG_BOT_TOKEN_VASILEVNA", "TOPIC_ID_GENERAL", "WEATHER_API_KEY", "DACHA_LAT", "DACHA_LON"]
    elif script_name == "post_milk.py":
        required += ["TG_BOT_TOKEN_OLYA", "TOPIC_ID_MILK"]
    elif script_name == "post_garden_vasilevna.py":
        required += ["TG_BOT_TOKEN_VASILEVNA", "TOPIC_ID_GARDEN"]
    elif script_name == "post_garden_petrovich.py":
        required += ["TG_BOT_TOKEN_PETROVICH", "TOPIC_ID_GARDEN"]
    elif script_name == "post_garden_edik.py":
        required += ["TG_BOT_TOKEN_EDIK", "TOPIC_ID_EDIK"]
    elif script_name == "post_humor.py":
        required += ["TG_BOT_TOKEN_VASILEVNA", "TG_BOT_TOKEN_PETROVICH", "TG_BOT_TOKEN_EDIK", "TOPIC_ID_HUMOR"]
    elif script_name == "post_daily_rotation.py":
        # Заранее неизвестно, какое действие цикла выпадет на сегодня,
        # поэтому проверяем объединение переменных всех четырёх действий —
        # лучше упасть сразу с понятной ошибкой в CI, чем на полпути.
        required += [
            "TG_BOT_TOKEN_VASILEVNA", "TG_BOT_TOKEN_PETROVICH", "TG_BOT_TOKEN_EDIK",
            "TOPIC_ID_GARDEN", "TOPIC_ID_EDIK", "TOPIC_ID_HUMOR",
        ]
    elif script_name == "cleanup_joins.py":
        required += ["TG_BOT_TOKEN_VASILEVNA"]

    # Проверка наличия переменных
    missing = [var for var in required if not os.environ.get(var)]
    
    # Для всех скриптов, кроме юмора и чистки, требуется хотя бы один ключ Gemini
    if script_name not in ["post_humor.py", "cleanup_joins.py"]:
        gemini_keys = [os.environ.get(f"GEMINI_KEY_{i}") for i in range(1, 11)]
        if not any(gemini_keys):
            missing.append("GEMINI_KEY_1..10 (хотя бы один)")

    if missing:
        raise ValueError(
            f"Отсутствуют обязательные переменные окружения для запуска {script_name}: {', '.join(missing)}"
        )


def run_safely(main_func: Callable[[], None], label: str) -> None:
    """Запускает main_func(), ловит любое исключение, логирует и уведомляет."""
    try:
        _validate_env_variables()
        main_func()
    except Exception as exc:  # noqa: BLE001 — намеренно ловим всё, чтобы пост не падал молча
        logger.error("%s: не отправился: %s\n%s", label, exc, traceback.format_exc())
        _log_error_to_file(exc)
        _notify_admin(label, exc)
        # Не пробрасываем исключение дальше: cron должен видеть код возврата 0,
        # чтобы не заспамить почту root'а при каждом временном сбое Gemini/OWM.
