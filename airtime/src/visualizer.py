"""
visualizer.py — Affichage et export de la grille et des métriques
"""
from __future__ import annotations
import json
from pathlib import Path
from src.models import Schedule, DAYS_OF_WEEK


def print_schedule(schedule: Schedule, day: str | None = None) -> None:
    """Affiche la grille d'un jour (ou de la semaine entière) dans le terminal."""
    days = [day] if day else DAYS_OF_WEEK
    for d in days:
        items = schedule.by_day(d)
        print(f"\n{'═'*70}")
        print(f"  {d.upper()}")
        print(f"{'═'*70}")
        print(f"{'Heure':<8} {'Fin':<8} {'Tranche':<18} {'Titre':<35} {'Profit':>10}")
        print(f"{'─'*70}")
        for item in items:
            title = item.program.title[:33]
            print(
                f"{item.start_time_str:<8} {item.end_time_str:<8} "
                f"{item.slot_name:<18} {title:<35} "
                f"{item.profit:>10,.0f}€"
            )


def print_metrics(metrics: dict) -> None:
    """Affiche les métriques clés dans le terminal."""
    print(f"\n{'═'*50}")
    print("  MÉTRIQUES HEBDOMADAIRES")
    print(f"{'═'*50}")
    print(f"  Programmes planifiés : {metrics['total_programs']}")
    print(f"  Revenus publicitaires: {metrics['total_revenue_€']:>15,.0f} €")
    print(f"  Coûts de diffusion   : {metrics['total_cost_€']:>15,.0f} €")
    print(f"  Profit net           : {metrics['total_profit_€']:>15,.0f} €")
    print(f"  Audience totale      : {metrics['total_audience']:>15,.0f}")
    print(f"  ROI                  : {metrics['roi_%']:>14.1f} %")
    print(f"\n  {'Jour':<12} {'Programmes':>11} {'Profit':>15}")
    print(f"  {'─'*40}")
    for day, d in metrics["by_day"].items():
        print(f"  {day:<12} {d['programs']:>11} {d['profit_€']:>15,.0f} €")
    print(f"\n  Distribution des genres :")
    for genre, count in sorted(
        metrics["genre_distribution"].items(), key=lambda x: -x[1]
    ):
        print(f"    {genre:<25} {count:>4} diffusions")


def export_schedule_json(schedule: Schedule, path: str | Path) -> None:
    """Exporte la grille au format JSON."""
    data = []
    for item in schedule.items:
        data.append({
            "id": item.program.id,
            "title": item.program.title,
            "genre": item.program.genre,
            "day": item.day,
            "slot": item.slot_name,
            "start": item.start_time_str,
            "end": item.end_time_str,
            "duration_min": item.program.duration_minutes,
            "audience": round(item.real_audience),
            "revenue_€": round(item.revenue, 2),
            "cost_€": item.program.cost,
            "profit_€": round(item.profit, 2),
        })
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → Grille exportée : {path}")


def export_metrics_json(metrics: dict, path: str | Path) -> None:
    """Exporte les métriques au format JSON."""
    Path(path).write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  → Métriques exportées : {path}")
