"""
Дневная ротация постов в "садовый" блок расписания (раньше это были
отдельные ежедневные посты Васильевны в 12:00 и Петровича в 17:00, плюс
отдельный ежедневный пост юмора в 19:00 — теперь всё это объединено в
один 5-дневный цикл, чтобы освободить место для Эдика и Оли):

    День 1 — Нина Васильевна, пост в "Дача, сад, огород"
    День 2 — Эдик, пост в свой топик (тема из стека, текст с нуля от Gemini)
    День 3 — Петрович, пост в "Дача, сад, огород"
    День 4 — "Дачный юмор" (Васильевна, Петрович, Эдик по очереди)
    День 5 — Оля, пост в "Дача, сад, огород"

Цикл считается от CYCLE_START_DATE (день 1 = Васильевна). День недели
вычисляется как ((сегодня - CYCLE_START_DATE).days % 5).

Скрипт запускается ОДИН раз в день (одним workflow/cron) и сам решает,
какое действие сегодня нужно выполнить — это удобнее, чем держать 5
отдельных cron-расписания и следить, чтобы они не разъехались.
"""

import datetime

from run_safely import run_safely

import post_garden_vasilevna
import post_garden_edik
import post_garden_petrovich
import post_humor
import post_garden_olya

# День 1 цикла (Васильевна) — 14 июля 2026.
CYCLE_START_DATE = datetime.date(2026, 7, 13)

# Порядок действий в цикле, индекс 0..4.
CYCLE_ACTIONS = [
    ("Васильевна (сад)", post_garden_vasilevna.main),
    ("Эдик (сад)", post_garden_edik.main),
    ("Петрович (сад)", post_garden_petrovich.main),
    ("Дачный юмор", post_humor.main),
    ("Оля (сад)", post_garden_olya.main),
]


def get_cycle_day(today: datetime.date | None = None) -> int:
    """Возвращает индекс дня цикла 0..4 для переданной даты (по умолчанию — сегодня)."""
    today = today or datetime.date.today()
    delta_days = (today - CYCLE_START_DATE).days
    return delta_days % 5


def main() -> None:
    cycle_day = get_cycle_day()
    label, action = CYCLE_ACTIONS[cycle_day]
    print(f"Ротация: день цикла {cycle_day + 1}/4 — {label}.")
    action()


if __name__ == "__main__":
    run_safely(main, label="Дневная ротация (Васильевна/Эдик/Петрович/Юмор)")
