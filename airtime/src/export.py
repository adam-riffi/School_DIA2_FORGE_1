from __future__ import annotations

from typing import Dict, List, Tuple

from .config import DAYS_FR, SLOT_MINUTES, TIME_BANDS, DAY_COEFF, AD_BREAK_MINUTES, ad_breaks_for_program
from .preprocess import Precomputed
from .timeutils import time_from_slot_index, slot_index_from_time


def _band_for_slot(slot: int) -> Dict:
    for b in TIME_BANDS:
        s = slot_index_from_time(b["start"])
        e = slot_index_from_time(b["end"])
        if s <= slot < e:
            return b
    return TIME_BANDS[0]


def _estimate_ad_revenue(prog, start_slot: int, day_name: str) -> int:
    """Estimate ad revenue for a program based on audience and CPM."""
    band = _band_for_slot(start_slot)
    cpm = band["cpm"]  # cost per mille (per 1000 viewers)
    day_coeff = DAY_COEFF.get(day_name, 1.0)
    audience = int(prog.base_audience * band["aud_mult"] * day_coeff)
    breaks = ad_breaks_for_program(prog.genre, prog.duration_minutes)
    ad_minutes = breaks * AD_BREAK_MINUTES
    # Revenue = audience/1000 * CPM * ad_minutes
    revenue = int(audience / 1000 * cpm * ad_minutes)
    return revenue


def starts_to_schedule(pre: Precomputed, starts: List[Tuple[int, int, int]]) -> Dict:
    out = {"days": []}

    starts_by_day = {d: [] for d in range(7)}
    for d, s, p in starts:
        starts_by_day[d].append((s, p))

    weekly_cost = 0
    weekly_revenue = 0

    for d in range(7):
        items = []
        day_cost = 0
        day_revenue = 0
        day_name = DAYS_FR[d]
        for s, p in sorted(starts_by_day[d]):
            prog = pre.programs[p]
            dur = int(prog.duration_minutes)
            end_slot = s + pre.duration_slots[p]
            cost = int(prog.cost)
            revenue = _estimate_ad_revenue(prog, s, day_name)
            day_cost += cost
            day_revenue += revenue
            items.append({
                "start_slot": s,
                "end_slot": end_slot,
                "start_time": time_from_slot_index(s),
                "end_time": time_from_slot_index(end_slot),
                "program_id": prog.id,
                "title": prog.title,
                "genre": prog.genre,
                "subgenre": prog.subgenre,
                "duration_minutes": dur,
                "cost": cost,
                "ad_revenue": revenue,
            })
        weekly_cost += day_cost
        weekly_revenue += day_revenue
        out["days"].append({
            "day": day_name,
            "items": items,
            "day_cost": day_cost,
            "day_revenue": day_revenue,
            "day_profit": day_revenue - day_cost,
        })

    out["budget_summary"] = {
        "weekly_cost": weekly_cost,
        "weekly_revenue": weekly_revenue,
        "weekly_profit": weekly_revenue - weekly_cost,
        "budget_limit": 5_000_000,
        "budget_used_pct": round(weekly_cost / 5_000_000 * 100, 1),
    }
    return out
