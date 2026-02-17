"""
main.py — Point d'entrée principal du projet AIRTIME
Usage : python main.py [--day <Lundi|...|Dimanche>]
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from src.loader import load_programs
from src.optimizer import greedy_schedule, local_search
from src.evaluator import evaluate
from src.visualizer import print_schedule, print_metrics, export_schedule_json, export_metrics_json


def main() -> None:
    parser = argparse.ArgumentParser(description="AIRTIME – Optimisation grille TV 7 jours")
    parser.add_argument(
        "--day", type=str, default=None,
        help="Afficher uniquement un jour (ex: Lundi)"
    )
    parser.add_argument(
        "--no-local-search", action="store_true",
        help="Désactiver la recherche locale (plus rapide)"
    )
    args = parser.parse_args()

    data_path = Path("data/programs.json")
    results_path = Path("results")
    results_path.mkdir(exist_ok=True)

    # ── Chargement ──────────────────────────────────────────────
    print("\n[1/4] Chargement du catalogue de programmes...")
    programs = load_programs(data_path)
    print(f"      {len(programs)} programmes chargés.")

    # ── Planification gloutonne ──────────────────────────────────
    print("\n[2/4] Planification gloutonne (greedy)...")
    greedy = greedy_schedule(programs)
    print(f"      {greedy.program_count} émissions planifiées.")
    print(f"      Profit initial : {greedy.total_profit:,.0f} €")

    export_schedule_json(greedy, results_path / "schedule_greedy.json")
    export_metrics_json(evaluate(greedy), results_path / "metrics_greedy.json")

    # ── Optimisation par recherche locale ────────────────────────
    if not args.no_local_search:
        print("\n[3/4] Optimisation par recherche locale (500 itérations)...")
        optimized = local_search(greedy, programs, iterations=500)
        gain = optimized.total_profit - greedy.total_profit
        print(f"      Profit optimisé : {optimized.total_profit:,.0f} €  (gain : +{gain:,.0f} €)")
        export_schedule_json(optimized, results_path / "schedule_optimized.json")
        export_metrics_json(evaluate(optimized), results_path / "metrics_optimized.json")
        final = optimized
    else:
        final = greedy

    # ── Affichage ────────────────────────────────────────────────
    print("\n[4/4] Résultats finaux")
    metrics = evaluate(final)
    print_metrics(metrics)
    print_schedule(final, day=args.day)

    print(f"\n✓ Fichiers de résultats générés dans : {results_path.resolve()}/\n")


if __name__ == "__main__":
    main()
