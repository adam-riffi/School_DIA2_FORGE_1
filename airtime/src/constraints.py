"""
constraints.py — Vérification des contraintes de diffusion
"""
from __future__ import annotations
from datetime import date, timedelta
from src.models import Program, DAYS_OF_WEEK


# Date de référence : début de la semaine planifiée (Lundi 17 février 2026)
SCHEDULE_START_DATE = date(2026, 2, 17)


def day_date(day: str) -> date:
    """Retourne la date réelle du jour de la semaine planifiée."""
    idx = DAYS_OF_WEEK.index(day)
    return SCHEDULE_START_DATE + timedelta(days=idx)


def check_rerun_allowed(program: Program, day: str) -> bool:
    """Vérifie que le délai minimum entre deux diffusions est respecté."""
    if program.last_broadcast_date is None:
        return True
    broadcast_date = day_date(day)
    elapsed = (broadcast_date - program.last_broadcast_date).days
    return elapsed >= program.min_rerun_days


def check_slot_allowed(program: Program, slot_name: str) -> bool:
    """Vérifie que le créneau n'est pas interdit pour ce programme."""
    return slot_name not in program.forbidden_slots


def check_unique_per_week(program: Program, used_ids: set[str]) -> bool:
    """Un même programme ne peut être diffusé qu'une fois par semaine."""
    return program.id not in used_ids


def check_series_max_per_week(
    program: Program,
    series_count: dict[str, int],  # {title_base: nb_diffusions}
) -> bool:
    """Respecte la limite d'épisodes d'une série par semaine."""
    if not program.is_series():
        return True
    max_ep = program.max_episodes_per_week or 1
    key = f"{program.title.split('S0')[0].strip()}"
    return series_count.get(key, 0) < max_ep


def check_slot_fits(
    slot_start: int,
    slot_end: int,
    program_duration: int,
    current_time: int,
) -> bool:
    """Vérifie que le programme tient dans la tranche horaire restante."""
    return current_time + program_duration <= slot_end


def check_fixed_day(program: Program, day: str) -> bool:
    """Si le programme a des jours fixes, vérifie la cohérence."""
    if not program.fixed_days:
        return True
    return day in program.fixed_days


def is_eligible(
    program: Program,
    slot_name: str,
    day: str,
    used_ids: set[str],
    series_count: dict[str, int],
    slot_start: int,
    slot_end: int,
    current_time: int,
) -> bool:
    """
    Vérifie l'ensemble des contraintes pour un programme dans un créneau.
    Retourne True si le programme peut être planifié.
    """
    return (
        check_slot_allowed(program, slot_name)
        and check_rerun_allowed(program, day)
        and check_unique_per_week(program, used_ids)
        and check_series_max_per_week(program, series_count)
        and check_slot_fits(slot_start, slot_end, program.duration_minutes, current_time)
        and check_fixed_day(program, day)
    )
