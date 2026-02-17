"""
audience.py — Modèle d'audience
Formule : Audience_réelle = base × coeff_tranche × coeff_héritage × coeff_jour
"""
from __future__ import annotations
from src.models import Program, SLOT_COEFF, DAY_COEFF


def compute_audience(
    program: Program,
    slot_name: str,
    day: str,
    previous_audience: float = 0.0,
    previous_slot: str | None = None,
) -> float:
    """
    Calcule l'audience réelle d'un programme.

    Parameters
    ----------
    program          : Programme à diffuser
    slot_name        : Tranche horaire (ex: "Prime Time")
    day              : Jour de la semaine (ex: "Lundi")
    previous_audience: Audience du programme précédent (héritage)
    previous_slot    : Tranche du programme précédent (pour le bonus)
    """
    coeff_slot = SLOT_COEFF.get(slot_name, 1.0)
    coeff_day  = DAY_COEFF.get(day, 1.0)

    # Coefficient d'héritage : ±20% selon l'audience précédente
    if previous_audience > 0 and program.base_audience > 0:
        ratio = previous_audience / program.base_audience
        if ratio > 1.2:
            coeff_heritage = 1.2
        elif ratio < 0.8:
            coeff_heritage = 0.8
        else:
            coeff_heritage = 1.0
    else:
        coeff_heritage = 1.0

    # Bonus si tranche préférée
    if slot_name in program.preferred_slots:
        bonus = 1.05
    else:
        bonus = 1.0

    return program.base_audience * coeff_slot * coeff_heritage * coeff_day * bonus
