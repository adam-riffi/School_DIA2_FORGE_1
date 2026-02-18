from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

from .config import SLOT_MINUTES, SCHEDULE_START


def parse_hhmm(h: str) -> Tuple[int, int]:
    hh, mm = h.split(":")
    return int(hh), int(mm)


def minutes_from_schedule_start(hhmm: str) -> int:
    """
    Convertit une heure HH:MM en minutes depuis 06:00.
    Gère le passage après minuit (00:xx, 01:xx, 02:00) comme le lendemain.
    """
    sh, sm = parse_hhmm(SCHEDULE_START)
    h, m = parse_hhmm(hhmm)

    start = sh * 60 + sm
    cur = h * 60 + m
    if cur < start:
        cur += 24 * 60
    return cur - start


def slot_index_from_time(hhmm: str) -> int:
    return minutes_from_schedule_start(hhmm) // SLOT_MINUTES


def time_from_slot_index(slot: int) -> str:
    sh, sm = parse_hhmm(SCHEDULE_START)
    total = sh * 60 + sm + slot * SLOT_MINUTES
    total %= 24 * 60
    hh = total // 60
    mm = total % 60
    return f"{hh:02d}:{mm:02d}"
