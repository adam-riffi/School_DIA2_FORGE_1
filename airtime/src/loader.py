from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Program:
    id: str
    title: str
    genre: str
    subgenre: str
    duration_minutes: int
    cost: int
    base_audience: int
    origin: str
    year: int
    age_rating: str

    # Contractuel / droits
    independent: Optional[bool] = None
    rights_start: Optional[str] = None          # "YYYY-MM-DD"
    rights_end: Optional[str] = None            # "YYYY-MM-DD"
    in_production: Optional[bool] = None

    # Historique / fréquence
    last_broadcast_date: Optional[str] = None
    min_rerun_days: Optional[int] = None

    # Habitudes
    usual_day: Optional[str] = None
    usual_time: Optional[str] = None
    is_new: Optional[bool] = None               # nouveauté (C.7)
    is_exclusive: Optional[bool] = None         # exclusivité (C.7)

    fixed_time: Optional[str] = None
    fixed_days: Optional[List[str]] = None

    # Audience / diffusion
    target_audience: Optional[List[str]] = None
    first_broadcast: Optional[bool] = None

    # Créneaux
    preferred_slots: Optional[List[str]] = None
    forbidden_slots: Optional[List[str]] = None

    # Compatibilité de genre
    compatible_genres: Optional[List[str]] = None
    incompatible_genres: Optional[List[str]] = None

    # Type de magazine
    health_magazine: Optional[bool] = None

    # Séries / épisodes
    season: Optional[int] = None
    episode: Optional[int] = None
    total_episodes: Optional[int] = None
    max_episodes_per_week: Optional[int] = None
    previous_episode: Optional[str] = None


def load_programs(path: str) -> List[Program]:
    raw = json.loads(open(path, "r", encoding="utf-8").read())
    return [Program(**p) for p in raw]
