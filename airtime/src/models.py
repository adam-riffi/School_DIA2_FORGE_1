"""
models.py — Classes de données : Program, TimeSlot, ScheduledItem, Schedule
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time
from typing import Optional


# ─────────────────────────────────────────────────
# Constantes : tranches horaires
# ─────────────────────────────────────────────────

SLOTS_DEFINITION: dict[str, tuple[str, str]] = {
    "Matin":           ("06:00", "09:00"),
    "Matinée":         ("09:00", "12:00"),
    "Midi":            ("12:00", "14:00"),
    "Après-midi":      ("14:00", "18:00"),
    "Access Prime":    ("18:00", "20:00"),
    "Prime Time":      ("20:00", "22:30"),
    "Deuxième partie": ("22:30", "00:30"),
    "Nuit":            ("00:30", "02:00"),
}

SLOT_COEFF: dict[str, float] = {
    "Matin":           0.6,
    "Matinée":         0.4,
    "Midi":            0.9,
    "Après-midi":      0.5,
    "Access Prime":    1.1,
    "Prime Time":      1.3,
    "Deuxième partie": 0.8,
    "Nuit":            0.3,
}

DAY_COEFF: dict[str, float] = {
    "Lundi":    1.0,
    "Mardi":    1.0,
    "Mercredi": 1.0,
    "Jeudi":    1.0,
    "Vendredi": 1.0,
    "Samedi":   1.1,
    "Dimanche": 1.2,
}

CPM: dict[str, float] = {
    "Matin":           7.0,
    "Matinée":         5.0,
    "Midi":            9.0,
    "Après-midi":      6.0,
    "Access Prime":    11.0,
    "Prime Time":      15.0,
    "Deuxième partie": 10.0,
    "Nuit":            4.0,
}

DAYS_OF_WEEK = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


# ─────────────────────────────────────────────────
# Classe Program
# ─────────────────────────────────────────────────

@dataclass
class Program:
    id: str
    title: str
    genre: str
    subgenre: str
    duration_minutes: int
    cost: float
    base_audience: int
    origin: str
    year: int
    age_rating: str
    target_audience: list[str]
    first_broadcast: bool
    last_broadcast_date: Optional[date]
    min_rerun_days: int
    preferred_slots: list[str]
    forbidden_slots: list[str]
    compatible_genres: list[str]
    incompatible_genres: list[str]
    # Champs optionnels séries
    season: Optional[int] = None
    episode: Optional[int] = None
    total_episodes: Optional[int] = None
    max_episodes_per_week: Optional[int] = None
    usual_day: Optional[str] = None
    usual_time: Optional[str] = None
    previous_episode: Optional[str] = None
    # Champs optionnels fixes
    fixed_time: Optional[str] = None
    fixed_days: list[str] = field(default_factory=list)

    @property
    def slots_15min(self) -> int:
        """Nombre de slots de 15 minutes occupés."""
        return (self.duration_minutes + 14) // 15

    def is_series(self) -> bool:
        return self.episode is not None

    def is_fixed(self) -> bool:
        return self.fixed_time is not None


# ─────────────────────────────────────────────────
# Classe ScheduledItem
# ─────────────────────────────────────────────────

@dataclass
class ScheduledItem:
    program: Program
    day: str              # ex: "Lundi"
    slot_name: str        # ex: "Prime Time"
    start_minutes: int    # minutes depuis 00:00 (ex: 1200 = 20:00)
    real_audience: float
    revenue: float
    profit: float

    @property
    def start_time_str(self) -> str:
        h, m = divmod(self.start_minutes % 1440, 60)
        return f"{h:02d}:{m:02d}"

    @property
    def end_minutes(self) -> int:
        return self.start_minutes + self.program.duration_minutes

    @property
    def end_time_str(self) -> str:
        h, m = divmod(self.end_minutes % 1440, 60)
        return f"{h:02d}:{m:02d}"


# ─────────────────────────────────────────────────
# Classe Schedule (grille hebdomadaire)
# ─────────────────────────────────────────────────

@dataclass
class Schedule:
    items: list[ScheduledItem] = field(default_factory=list)

    def by_day(self, day: str) -> list[ScheduledItem]:
        return sorted(
            [i for i in self.items if i.day == day],
            key=lambda x: x.start_minutes
        )

    @property
    def total_revenue(self) -> float:
        return sum(i.revenue for i in self.items)

    @property
    def total_cost(self) -> float:
        return sum(i.program.cost for i in self.items)

    @property
    def total_profit(self) -> float:
        return sum(i.profit for i in self.items)

    @property
    def total_audience(self) -> float:
        return sum(i.real_audience for i in self.items)

    @property
    def program_count(self) -> int:
        return len(self.items)

    def programs_used_ids(self) -> set[str]:
        return {i.program.id for i in self.items}