"""
loader.py — Chargement et nettoyage du catalogue programs.json
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from src.models import Program


def _fix_encoding(s: str) -> str:
    """Corrige les chaînes mal encodées (cp1252 → utf-8)."""
    for codec in ("cp1252", "latin1"):
        try:
            return s.encode(codec).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return s


def _fix_obj(obj: object) -> object:
    if isinstance(obj, str):
        return _fix_encoding(obj)
    if isinstance(obj, list):
        return [_fix_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {_fix_obj(k): _fix_obj(v) for k, v in obj.items()}
    return obj


def load_programs(path: str | Path = "data/programs.json") -> list[Program]:
    """Charge le catalogue de programmes depuis un fichier JSON."""
    with open(path, encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    programs: list[Program] = []
    for entry in raw:
        entry = _fix_obj(entry)

        lbd = entry.get("last_broadcast_date")
        last_date = date.fromisoformat(lbd) if lbd else None

        prog = Program(
            id=entry["id"],
            title=entry.get("title", ""),
            genre=entry.get("genre", ""),
            subgenre=entry.get("subgenre", ""),
            duration_minutes=int(entry.get("duration_minutes", 30)),
            cost=float(entry.get("cost", 0)),
            base_audience=int(entry.get("base_audience", 0)),
            origin=entry.get("origin", ""),
            year=int(entry.get("year", 2000)),
            age_rating=entry.get("age_rating", "Tout public"),
            target_audience=entry.get("target_audience", []),
            first_broadcast=bool(entry.get("first_broadcast", False)),
            last_broadcast_date=last_date,
            min_rerun_days=int(entry.get("min_rerun_days", 30)),
            preferred_slots=entry.get("preferred_slots", []),
            forbidden_slots=entry.get("forbidden_slots", []),
            compatible_genres=entry.get("compatible_genres", []),
            incompatible_genres=entry.get("incompatible_genres", []),
            season=entry.get("season"),
            episode=entry.get("episode"),
            total_episodes=entry.get("total_episodes"),
            max_episodes_per_week=entry.get("max_episodes_per_week"),
            usual_day=entry.get("usual_day"),
            usual_time=entry.get("usual_time"),
            previous_episode=entry.get("previous_episode"),
            fixed_time=entry.get("fixed_time"),
            fixed_days=entry.get("fixed_days", []),
        )
        programs.append(prog)

    return programs
