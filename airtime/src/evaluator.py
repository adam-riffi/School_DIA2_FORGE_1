"""
evaluator.py — Calcul des métriques de performance d'une grille
"""
from __future__ import annotations
from src.models import Schedule, DAYS_OF_WEEK

try:
    from src.models import SLOT_ORDER  # type: ignore[attr-defined]
except ImportError:
    SLOT_ORDER = [
        "Matin", "Matinée", "Midi", "Après-midi",
        "Access Prime", "Prime Time", "Deuxième partie", "Nuit",
    ]


def evaluate(schedule: Schedule) -> dict:
    """Retourne un dictionnaire complet de métriques."""
    metrics: dict = {
        "total_programs": schedule.program_count,
        "total_revenue_€": round(schedule.total_revenue, 2),
        "total_cost_€":    round(schedule.total_cost, 2),
        "total_profit_€":  round(schedule.total_profit, 2),
        "total_audience":  round(schedule.total_audience),
        "avg_audience_per_program": round(
            schedule.total_audience / max(schedule.program_count, 1)
        ),
        "roi_%": round(
            (schedule.total_profit / max(schedule.total_cost, 1)) * 100, 2
        ),
        "by_day": {},
        "by_slot": {},
        "genre_distribution": {},
    }

    # Par jour
    for day in DAYS_OF_WEEK:
        day_items = schedule.by_day(day)
        metrics["by_day"][day] = {
            "programs": len(day_items),
            "profit_€": round(sum(i.profit for i in day_items), 2),
            "audience": round(sum(i.real_audience for i in day_items)),
        }

    # Par tranche
    slot_names = [
        "Matin", "Matinée", "Midi", "Après-midi",
        "Access Prime", "Prime Time", "Deuxième partie", "Nuit",
    ]
    for slot in slot_names:
        slot_items = [i for i in schedule.items if i.slot_name == slot]
        metrics["by_slot"][slot] = {
            "programs": len(slot_items),
            "profit_€": round(sum(i.profit for i in slot_items), 2),
        }

    # Distribution des genres
    for item in schedule.items:
        g = item.program.genre
        metrics["genre_distribution"][g] = metrics["genre_distribution"].get(g, 0) + 1

    return metrics
