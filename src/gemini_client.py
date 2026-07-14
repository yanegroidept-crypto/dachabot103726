"""
Клиент для Gemini API с ротацией из 10 ключей.

Индекс текущего ключа хранится в state/gemini_key_index.json и
сдвигается на 1 после КАЖДОГО запроса (успешного или нет), чтобы
не заваливать один и тот же ключ повторными неудачными попытками.

Ключи ожидаются в переменных окружения GEMINI_KEY_1 ... GEMINI_KEY_10.

Логика модели/ретраев — цепочка из двух моделей, от более
качественной/быстрой к самой дешёвой:
1. gemini-3.5-flash — до MAX_RETRIES_PER_MODEL попыток
   (с ротацией ключа перед каждой попыткой).
2. Если все попытки провалились — gemini-3.1-flash-lite, тоже до
   MAX_RETRIES_PER_MODEL попыток.
Если не сработала ни одна модель — пробрасываем последнее исключение.
"""

import json
import logging
import os
import time
from pathlib import Path

from google import genai

logger = logging.getLogger(__name__)

KEY_INDEX_PATH = Path(__file__).resolve().parent.parent / "state" / "gemini_key_index.json"
NUM_KEYS = 10

# Цепочка моделей по убыванию приоритета.
# Может быть переопределена через переменную окружения GEMINI_MODEL_CHAIN
# (перечисление через запятую, например: GEMINI_MODEL_CHAIN=gemini-2.5-pro,gemini-2.5-flash).
DEFAULT_MODEL_CHAIN = ["gemini-3.5-flash", "gemini-3.1-flash-lite"]

def _get_model_chain() -> list[str]:
    env_val = os.environ.get("GEMINI_MODEL_CHAIN")
    if env_val:
        models = [m.strip() for m in env_val.split(",") if m.strip()]
        if models:
            return models
    return DEFAULT_MODEL_CHAIN

MODEL_CHAIN = _get_model_chain()
DEFAULT_MODEL = MODEL_CHAIN[0]
MAX_RETRIES_PER_MODEL = 10
RETRY_DELAY_SECONDS = 2


def _get_keys() -> list[str]:
    keys = []
    for i in range(1, NUM_KEYS + 1):
        env_name = f"GEMINI_KEY_{i}"
        value = os.environ.get(env_name)
        if value:
            keys.append(value)
    if not keys:
        raise RuntimeError(
            "Не найдено ни одного ключа GEMINI_KEY_1..GEMINI_KEY_10 в переменных окружения"
        )
    return keys


def _load_index() -> int:
    if not KEY_INDEX_PATH.exists():
        return 0
    try:
        return json.loads(KEY_INDEX_PATH.read_text(encoding="utf-8"))["index"]
    except (json.JSONDecodeError, KeyError):
        return 0


def _save_index(idx: int) -> None:
    KEY_INDEX_PATH.write_text(json.dumps({"index": idx}), encoding="utf-8")


def _is_rate_limit_error(exc: Exception) -> bool:
    """
    Грубая эвристика: 429 / упоминание квоты/rate limit в тексте ошибки —
    повод крутить ключ. Всё остальное (400 невалидный prompt, таймаут сети
    и т.п.) ключ не чинит, но мы всё равно ротируем при неудаче (см.
    комментарий в generate()) — здесь эта функция используется только
    для логирования причины, чтобы отличать типы сбоев в логах.
    """
    text = str(exc).lower()
    return "429" in text or "quota" in text or "rate limit" in text or "resource_exhausted" in text


def _generate_once(prompt: str, model_name: str, keys: list[str]) -> str:
    """
    Один запрос к Gemini текущим ключом из ротации. Ротация всегда
    сдвигается на 1, независимо от результата: даже если ошибка не связана
    с конкретным ключом (например, невалидный prompt), следующая попытка
    всё равно пойдёт другим ключом — это не чинит проблему промпта, но и
    не вредит, а логирование по _is_rate_limit_error позволяет отличить
    в логах "ключ исчерпан" от "промпт/сеть сломаны".
    """
    idx = _load_index()
    key = keys[idx % len(keys)]

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        return response.text
    except Exception as exc:
        reason = "rate_limit" if _is_rate_limit_error(exc) else "other"
        logger.warning("Ключ #%d, модель %s: ошибка (%s): %s", idx % len(keys) + 1, model_name, reason, exc)
        raise
    finally:
        _save_index((idx + 1) % len(keys))


def validate_and_parse_json(raw: str) -> tuple[str, str]:
    """
    Проверяет, что ответ является валидным JSON, содержащим 'post_text'.
    Пытается исправить мелкие ошибки JSON или вытащить данные через regex.
    Если совсем ничего не получается — поднимает ValueError.
    """
    cleaned = clean_json_response(raw)
    
    # 1. Сначала пробуем прямой импорт через json.loads
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and "post_text" in data and data["post_text"]:
            post_text = data["post_text"]
            history_summary = data.get("history_summary") or ""
            return str(post_text).strip(), str(history_summary).strip()
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. Если стандартный json.loads не сработал, пробуем регулярные выражения
    # для поиска "post_text": "содержимое"
    import re
    match = re.search(r'"post_text"\s*:\s*"(.*?)"\s*(?:,|\s*})', cleaned, re.DOTALL)
    if match:
        post_text = match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
        if post_text:
            # Пытаемся также найти history_summary
            summary_match = re.search(r'"history_summary"\s*:\s*"(.*?)"\s*(?:,|\s*})', cleaned, re.DOTALL)
            history_summary = ""
            if summary_match:
                history_summary = summary_match.group(1).replace('\\"', '"').replace('\\n', '\n').strip()
            return post_text, history_summary

    # 3. Если мы не нашли post_text, но весь текст выглядит как нормальный пост без технических JSON-тегов
    # (например, когда модель проигнорировала JSON-инструкцию и выдала чистый текст).
    # Во избежание утечки системного промпта убедимся, что это не содержит открывающихся фигурных скобок и 'post_text'.
    if "{" not in cleaned and "post_text" not in cleaned and len(cleaned) > 20:
        lower_cleaned = cleaned.lower()
        is_refusal = any(word in lower_cleaned for word in ["к сожалению", "не могу", "ошибка", "извините"])
        if not is_refusal:
            return cleaned, ""

    raise ValueError("Ответ модели не содержит обязательное поле 'post_text' или имеет поврежденную структуру JSON")


def generate(prompt: str, model_chain: list[str] = MODEL_CHAIN) -> str:
    """
    Отправляет промпт в Gemini, проходя по цепочке моделей model_chain
    по порядку (по умолчанию MODEL_CHAIN: gemini-3.1-pro-preview →
    gemini-3.5-flash → gemini-3.1-flash-lite).

    На каждой модели — до MAX_RETRIES_PER_MODEL попыток подряд, с
    ротацией ключа перед каждой попыткой и валидацией формата.
    Если все попытки на модели провалились, переходим к следующей модели в цепочке.
    Если ни одна модель не сработала — пробрасывается последнее исключение.
    """
    keys = _get_keys()
    last_error: Exception | None = None

    for model_index, model_name in enumerate(model_chain):
        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                raw_response = _generate_once(prompt, model_name, keys)
                # Валидируем структуру ответа прямо в цикле попыток.
                # Если ответ не валиден, validate_and_parse_json поднимет ValueError,
                # и мы перейдем к следующей попытке (с ротацией ключа) или модели.
                validate_and_parse_json(raw_response)
                return raw_response
            except Exception as exc:  # noqa: BLE001 — нужно поймать любые ошибки API/сети/валидации
                last_error = exc
                logger.warning(
                    "Gemini (%s): попытка %d/%d неудачна: %s",
                    model_name, attempt, MAX_RETRIES_PER_MODEL, exc,
                )
                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(RETRY_DELAY_SECONDS)

        is_last_model = model_index == len(model_chain) - 1
        if not is_last_model:
            next_model = model_chain[model_index + 1]
            logger.warning(
                "Gemini (%s): все %d попыток провалились, переключаюсь на %s",
                model_name, MAX_RETRIES_PER_MODEL, next_model,
            )

    logger.error("Gemini: все модели цепочки (%s) исчерпаны", ", ".join(model_chain))
    raise last_error


def clean_json_response(raw: str) -> str:
    """
    Gemini иногда оборачивает JSON в ```json ... ``` несмотря на инструкцию
    отвечать чистым JSON. Эта функция подчищает такие обёртки.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
        cleaned = cleaned.strip()
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned


def safe_parse_post_response(raw_response: str, default_summary: str) -> tuple[str, str]:
    """
    Пытается распарсить ответ Gemini как {"post_text": ..., "history_summary": ...}.
    Использует validate_and_parse_json для надежного извлечения.
    Если на этом этапе что-то пойдет не так (что маловероятно после валидации в generate()),
    использует резервные значения.

    Возвращает (post_text, history_summary).
    """
    try:
        post_text, summary = validate_and_parse_json(raw_response)
        if not summary:
            summary = default_summary
        return post_text, summary
    except Exception as exc:
        logger.warning(
            "Окончательный сбой парсинга ответа (%s), использую очищенный сырой ответ как пост",
            exc,
        )
        return clean_json_response(raw_response), default_summary
