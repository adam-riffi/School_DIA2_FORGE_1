"""
revenue.py — Calcul des recettes publicitaires et du profit
Formule : Recette = Audience × CPM × nb_écrans_pub
          Profit  = Recette - Coût_diffusion
"""
from __future__ import annotations
from src.models import Program, CPM


def nb_pub_screens(duration_minutes: int) -> int:
    """Nombre d'écrans publicitaires selon la durée (1 écran / 30 min)."""
    return max(1, duration_minutes // 30 * 3)


def compute_revenue(audience: float, slot_name: str, duration_minutes: int) -> float:
    """Calcule la recette publicitaire en euros."""
    cpm = CPM.get(slot_name, 7.0)
    screens = nb_pub_screens(duration_minutes)
    return (audience / 1000.0) * cpm * screens


def compute_profit(revenue: float, cost: float) -> float:
    """Profit net = recettes pub - coût diffusion."""
    return revenue - cost
