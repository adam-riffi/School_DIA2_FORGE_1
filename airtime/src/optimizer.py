"""
optimizer.py — Planificateur glouton + amélioration par recherche locale
Objectif : maximiser le profit hebdomadaire (recettes pub - coûts diffusion)
"""
from __future__ import annotations
import random
from typing import Optional
from src.models import (
    Program, Schedule, ScheduledItem,
    SLOTS_DEFINITION, DAYS_OF_WEEK,
)
from src.audience import compute_audience
from src.revenue import compute_revenue, compute_profit
from src.constraints import is_eligible


# ─────────────────────────────────────────────────
# Utilitaires : conversion horaire
# ─────────────────────────────────────────────────

def _hm_to_minutes(hm: str) -> int:
    """'20:00' → 1200"""
    h, m = map(int, hm.split(":"))
    return h * 60 + m


def _slot_bounds(slot_name: str) -> tuple[int, int]:
    """Retourne (start_min, end_min) en minutes depuis 00:00."""
    s, e = SLOTS_DEFINITION[slot_name]
    start = _hm_to_minutes(s)
    end   = _hm_to_minutes(e)
    # Nuit et Deuxième partie finissent après minuit
    if end <= start:
        end += 24 * 60
    return start, end


def _slot_duration(slot_name: str) -> int:
    s, e = _slot_bounds(slot_name)
    return e - s


# ─────────────────────────────────────────────────
# Évaluation d'un candidat
# ─────────────────────────────────────────────────

def _score_program(
    program: Program,
    slot_name: str,
    day: str,
    previous_audience: float,
) -> float:
    """Retourne le profit estimé d'un programme dans un créneau."""
    audience = compute_audience(program, slot_name, day, previous_audience)
    revenue  = compute_revenue(audience, slot_name, program.duration_minutes)
    return compute_profit(revenue, program.cost)


# ─────────────────────────────────────────────────
# Planificateur glouton (Greedy)
# ─────────────────────────────────────────────────

SLOT_ORDER = [
    "Matin", "Matinée", "Midi", "Après-midi",
    "Access Prime", "Prime Time", "Deuxième partie", "Nuit",
]


def greedy_schedule(programs: list[Program]) -> Schedule:
    """
    Planification gloutonne :
    Pour chaque tranche de chaque jour, sélectionne itérativement
    le programme maximisant le profit tout en respectant les contraintes.
    """
    schedule = Schedule()
    used_ids: set[str] = set()
    series_count: dict[str, int] = {}

    for day in DAYS_OF_WEEK:
        for slot_name in SLOT_ORDER:
            slot_start, slot_end = _slot_bounds(slot_name)
            current_time = slot_start
            previous_audience = 0.0

            while current_time < slot_end:
                remaining = slot_end - current_time

                # Candidats éligibles
                candidates = [
                    p for p in programs
                    if is_eligible(
                        p, slot_name, day, used_ids, series_count,
                        slot_start, slot_end, current_time
                    )
                    and p.duration_minutes <= remaining
                ]

                if not candidates:
                    break  # Plus de programme disponible pour ce créneau

                # Sélection du meilleur candidat (profit max)
                best = max(
                    candidates,
                    key=lambda p: _score_program(p, slot_name, day, previous_audience),
                )

                # Calcul des métriques
                audience = compute_audience(best, slot_name, day, previous_audience)
                revenue  = compute_revenue(audience, slot_name, best.duration_minutes)
                profit   = compute_profit(revenue, best.cost)

                item = ScheduledItem(
                    program=best,
                    day=day,
                    slot_name=slot_name,
                    start_minutes=current_time,
                    real_audience=audience,
                    revenue=revenue,
                    profit=profit,
                )
                schedule.items.append(item)

                # Mise à jour de l'état
                used_ids.add(best.id)
                previous_audience = audience
                current_time += best.duration_minutes

                # Comptage séries
                if best.is_series():
                    key = best.title.split("S0")[0].strip()
                    series_count[key] = series_count.get(key, 0) + 1

    return schedule


# ─────────────────────────────────────────────────
# Amélioration par recherche locale (swap)
# ─────────────────────────────────────────────────

def local_search(
    schedule: Schedule,
    programs: list[Program],
    iterations: int = 500,
    seed: int = 42,
) -> Schedule:
    """
    Amélioration par échanges (swaps) aléatoires :
    - Sélectionne deux items de la grille
    - Tente de les échanger
    - Conserve l'échange si le profit total augmente
    """
    random.seed(seed)
    best_schedule = schedule
    best_profit = schedule.total_profit

    for _ in range(iterations):
        if len(best_schedule.items) < 2:
            break

        # Copie légère des items
        items = list(best_schedule.items)
        i, j = random.sample(range(len(items)), 2)

        item_i = items[i]
        item_j = items[j]

        # Tentative d'échange des programmes
        prog_i, prog_j = item_i.program, item_j.program

        # Vérification des contraintes pour l'échange
        used_without_i = {it.program.id for it in items if it != item_i}
        used_without_j = {it.program.id for it in items if it != item_j}

        # prog_j dans le slot de item_i
        ok_j_in_i = (
            prog_j.id not in used_without_i
            and prog_j.id != prog_i.id
            and prog_j.duration_minutes <= _slot_duration(item_i.slot_name)
            and item_i.slot_name not in prog_j.forbidden_slots
        )
        # prog_i dans le slot de item_j
        ok_i_in_j = (
            prog_i.id not in used_without_j
            and prog_i.id != prog_j.id
            and prog_i.duration_minutes <= _slot_duration(item_j.slot_name)
            and item_j.slot_name not in prog_i.forbidden_slots
        )

        if not (ok_j_in_i and ok_i_in_j):
            continue

        # Recalcul des métriques après échange
        aud_i = compute_audience(prog_j, item_i.slot_name, item_i.day, 0.0)
        rev_i = compute_revenue(aud_i, item_i.slot_name, prog_j.duration_minutes)
        pft_i = compute_profit(rev_i, prog_j.cost)

        aud_j = compute_audience(prog_i, item_j.slot_name, item_j.day, 0.0)
        rev_j = compute_revenue(aud_j, item_j.slot_name, prog_i.duration_minutes)
        pft_j = compute_profit(rev_j, prog_i.cost)

        old_profit = item_i.profit + item_j.profit
        new_profit = pft_i + pft_j

        if new_profit > old_profit:
            # Appliquer l'échange
            items[i] = ScheduledItem(
                program=prog_j, day=item_i.day,
                slot_name=item_i.slot_name, start_minutes=item_i.start_minutes,
                real_audience=aud_i, revenue=rev_i, profit=pft_i,
            )
            items[j] = ScheduledItem(
                program=prog_i, day=item_j.day,
                slot_name=item_j.slot_name, start_minutes=item_j.start_minutes,
                real_audience=aud_j, revenue=rev_j, profit=pft_j,
            )
            new_schedule = Schedule(items=items)
            best_profit = new_schedule.total_profit
            best_schedule = new_schedule

    return best_schedule
