"""
Получение погоды по координатам СТ через OpenWeatherMap.

Используем два эндпоинта:
- /data/2.5/weather   — текущая погода (оставлено для обратной совместимости
                        и как запасной вариант, если прогноза нет).
- /data/2.5/forecast  — прогноз на 5 дней с шагом 3 часа (бесплатный план).
  Из него собираем:
    * прогноз на сегодня (утренний пост, get_today_forecast_summary)
    * прогноз на завтра + краткую сводку до конца недели
      (вечерний пост, get_evening_forecast_summary)

Если вы хотите использовать Open-Meteo (бесплатно, без ключа) вместо
OpenWeatherMap — смотрите закомментированную альтернативу внизу файла.
"""

import datetime
import os
from collections import defaultdict
from typing import Any

import requests

FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


def get_weather_summary() -> str:
    """Текущая погода (использовалась раньше и утром, и вечером)."""
    lat = os.environ["DACHA_LAT"]
    lon = os.environ["DACHA_LON"]
    api_key = os.environ["WEATHER_API_KEY"]

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ru"
    )
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    temp = data["main"]["temp"]
    feels_like = data["main"]["feels_like"]
    description = data["weather"][0]["description"]
    wind_speed = data["wind"]["speed"]
    humidity = data["main"]["humidity"]

    return (
        f"Температура: {temp:.0f}°C, ощущается как {feels_like:.0f}°C. "
        f"Описание: {description}. "
        f"Ветер: {wind_speed} м/с. Влажность: {humidity}%."
    )


def _fetch_forecast_raw() -> dict[str, Any]:
    lat = os.environ["DACHA_LAT"]
    lon = os.environ["DACHA_LON"]
    api_key = os.environ["WEATHER_API_KEY"]

    url = f"{FORECAST_URL}?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=ru"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()

    # OWM при превышении лимита/ошибке отдаёт 200 с {"cod": "429", "message": ...}
    # вместо ожидаемой структуры с "list" — тогда data["list"] упал бы с
    # непонятным KeyError. Проверяем явно и поднимаем понятную ошибку.
    forecast_list = data.get("list")
    if forecast_list is None:
        code = data.get("cod", "?")
        message = data.get("message", "нет списка прогноза в ответе")
        raise RuntimeError(f"OpenWeatherMap вернул ошибку (cod={code}): {message}")

    return data


def _group_by_date(entries: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        date_str = entry["dt_txt"].split(" ")[0]
        by_date[date_str].append(entry)
    return by_date


def _representative_entry(day_entries: list[dict[str, Any]]) -> dict[str, Any]:
    """Точка ближе к полудню — самая репрезентативная для дня."""
    for e in day_entries:
        hour = int(e["dt_txt"].split(" ")[1].split(":")[0])
        if 11 <= hour <= 14:
            return e
    return day_entries[len(day_entries) // 2]


def _day_summary(day_entries: list[dict[str, Any]]) -> str:
    """Короткая сводка по дню из 3-часовых точек прогноза (для списка дней)."""
    temps = [e["main"]["temp"] for e in day_entries]
    temp_min = min(temps)
    temp_max = max(temps)
    description = _representative_entry(day_entries)["weather"][0]["description"]
    return f"{temp_min:.0f}…{temp_max:.0f}°C, {description}"


def _forecast_for_date(by_date: dict[str, list[dict[str, Any]]], date_str: str, label: str) -> str | None:
    """
    Подробный прогноз (диапазон температур, описание, ветер, влажность)
    на конкретную дату из уже сгруппированного прогноза. Возвращает None,
    если данных на эту дату в ответе нет.
    """
    day_entries = by_date.get(date_str)
    if not day_entries:
        return None

    temps = [e["main"]["temp"] for e in day_entries]
    temp_min = min(temps)
    temp_max = max(temps)
    representative = _representative_entry(day_entries)
    description = representative["weather"][0]["description"]
    wind_speed = representative["wind"]["speed"]
    humidity = representative["main"]["humidity"]

    return (
        f"{label}: температура от {temp_min:.0f}°C до {temp_max:.0f}°C, "
        f"{description}. Ветер: {wind_speed} м/с. Влажность: {humidity}%."
    )


def get_today_forecast_summary() -> str:
    """
    Прогноз на сегодня (для утреннего поста в 08:30): диапазон
    температур на день, описание погоды днём, ветер и влажность.
    """
    data = _fetch_forecast_raw()
    by_date = _group_by_date(data["list"])
    today = datetime.date.today().isoformat()

    summary = _forecast_for_date(by_date, today, "Погода на сегодня")
    if summary is None:
        # Если по какой-то причине точки на сегодня уже не осталось в
        # 3-часовом прогнозе (например, все точки на сегодня уже в
        # прошлом) — берём текущую погоду, чтобы не падать совсем.
        return get_weather_summary()
    return summary


def get_tomorrow_forecast_summary() -> str:
    """
    Прогноз на завтра: диапазон температур, описание погоды днём,
    ветер и влажность на середину дня.
    """
    data = _fetch_forecast_raw()
    by_date = _group_by_date(data["list"])
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

    summary = _forecast_for_date(by_date, tomorrow, "Прогноз на завтра")
    if summary is None:
        # На случай если прогноза на завтра почему-то нет в ответе —
        # используем текущую погоду, чтобы не падать совсем.
        return get_weather_summary()
    return summary


def get_evening_forecast_summary() -> str:
    """
    Для вечернего поста: подробный прогноз на завтра + краткая сводка
    по дням до конца недели (что есть в 5-дневном прогнозе OWM).
    """
    data = _fetch_forecast_raw()
    by_date = _group_by_date(data["list"])

    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)

    tomorrow_str = get_tomorrow_forecast_summary()

    # Сводка по остальным дням, которые есть в прогнозе (обычно ещё
    # 3-4 дня после завтрашнего — весь горизонт бесплатного /forecast).
    weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    rest_of_week_lines = []
    for date_str in sorted(by_date.keys()):
        date_obj = datetime.date.fromisoformat(date_str)
        if date_obj <= tomorrow:
            continue
        weekday = weekday_names[date_obj.weekday()]
        rest_of_week_lines.append(f"{weekday} ({date_obj.strftime('%d.%m')}): {_day_summary(by_date[date_str])}")

    if rest_of_week_lines:
        rest_of_week_text = "Остальные дни (по имеющемуся прогнозу): " + "; ".join(rest_of_week_lines) + "."
    else:
        rest_of_week_text = ""

    return f"{tomorrow_str}\n{rest_of_week_text}".strip()


# --- Альтернатива без ключа (Open-Meteo) ---
#
# def get_weather_summary() -> str:
#     lat = os.environ["DACHA_LAT"]
#     lon = os.environ["DACHA_LON"]
#     url = (
#         "https://api.open-meteo.com/v1/forecast"
#         f"?latitude={lat}&longitude={lon}"
#         "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
#     )
#     response = requests.get(url, timeout=15)
#     response.raise_for_status()
#     data = response.json()["current"]
#     return (
#         f"Температура: {data['temperature_2m']}°C. "
#         f"Влажность: {data['relative_humidity_2m']}%. "
#         f"Ветер: {data['wind_speed_10m']} м/с. "
#         f"Код погодного явления (WMO): {data['weather_code']}."
#     )
