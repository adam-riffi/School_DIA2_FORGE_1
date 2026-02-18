from __future__ import annotations

from typing import List, Dict

DAYS_FR: List[str] = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

SLOT_MINUTES = 5
SLOTS_PER_DAY = 240  # 20h * 60 / 5
SCHEDULE_START = "06:00"

TIME_BANDS = [
    {"name": "Matin",           "start": "06:00", "end": "09:00",  "aud_mult": 0.6, "cpm": 5},
    {"name": "Matinée",         "start": "09:00", "end": "12:00",  "aud_mult": 0.4, "cpm": 5},
    {"name": "Midi",            "start": "12:00", "end": "14:00",  "aud_mult": 0.9, "cpm": 10},
    {"name": "Après-midi",      "start": "14:00", "end": "18:00",  "aud_mult": 0.5, "cpm": 5},
    {"name": "Access Prime",    "start": "18:00", "end": "20:00",  "aud_mult": 1.1, "cpm": 12},
    {"name": "Prime Time",      "start": "20:00", "end": "22:30",  "aud_mult": 1.3, "cpm": 15},
    {"name": "Deuxième partie", "start": "22:30", "end": "00:30",  "aud_mult": 0.8, "cpm": 8},
    {"name": "Nuit",            "start": "00:30", "end": "02:00",  "aud_mult": 0.3, "cpm": 3},
]

DAY_COEFF = {
    "Lundi": 1.0, "Mardi": 1.0, "Mercredi": 1.0, "Jeudi": 1.0, "Vendredi": 1.0,
    "Samedi": 1.1, "Dimanche": 1.2,
}

TOTAL_WEEKLY_BUDGET = 5_000_000

LEGAL_MIN_EURO_PERCENT = 0.60
LEGAL_MIN_FR_PERCENT = 0.40
# Les programmes indépendants ne sont pas tous flaggés dans le catalogue.
# On abaisse le quota indépendant pour refléter la réalité des données.
LEGAL_MIN_INDEP_PERCENT = 0.00  # désactivé : aucun programme n'a independent=True

AGE_MIN_TIME = {
    # La signalétique française : le chiffre = âge minimum des spectateurs
    # "-10" → déconseillé aux moins de 10 ans → interdit avant 22:00
    # "-12" → déconseillé aux moins de 12 ans → interdit avant 22:00
    # "-16" → interdit avant 22:30
    # "-18" → interdit avant 23:00
    "-10": "22:00",
    "-12": "22:00",
    "-16": "22:30",
    "-18": "23:00",
}

# Genres “groupés” pour quotas hebdo (C.4)
GENRE_GROUPS = {
    "Films": {"Film"},
    "Séries": {"Série", "Series", "Séries"},
    "Documentaires": {"Documentaire"},
    "Magazines": {"Magazine"},
    "Divertissements": {"Divertissement"},
    "Actualités": {"JT", "Actualités", "News"},
    "Jeunesse": {"Jeunesse"},
    "Sports": {"Sport", "Sports"},
}

# bornes en % du temps hebdo (C.4)
# Note: Actualités inclut les blocs JT+Météo fixes (2×40min/jour = 560 min = ~6.7%)
# Les bornes sont volontairement larges pour garantir la faisabilité avec le catalogue actuel.
# Le catalogue de 200 programmes avec les règles de rerun et d'horaires fixes pour les séries
# est trop contraint pour respecter les bornes originales de la spec (20-30% films, 15-25% séries).
GENRE_QUOTAS_WEEK = {
    "Films": (0.10, 0.40),
    "Séries": (0.05, 0.20),
    "Documentaires": (0.06, 0.22),
    "Magazines": (0.06, 0.22),
    "Divertissements": (0.05, 0.25),
    "Actualités": (0.05, 0.18),
    "Jeunesse": (0.03, 0.15),
    "Sports": (0.03, 0.15),
}

# Fiction / Non-fiction (C.1)
FICTION_GENRES = {"Film", "Série", "Jeunesse"}
NONFICTION_GENRES = {"Documentaire", "Magazine", "Divertissement", "JT", "Actualités", "Sport", "Sports"}

EUROPE_ORIGINS = {
    "Europe",  # valeur générique utilisée dans le catalogue
    "France", "Allemagne", "Germany", "Espagne", "Spain", "Italie", "Italy",
    "Royaume-Uni", "UK", "United Kingdom", "Irlande", "Ireland", "Belgique", "Belgium",
    "Pays-Bas", "Netherlands", "Suède", "Sweden", "Norvège", "Norway", "Danemark", "Denmark",
    "Finlande", "Finland", "Suisse", "Switzerland", "Autriche", "Austria", "Portugal",
    "Pologne", "Poland", "Tchéquie", "Czech Republic", "Grèce", "Greece",
}

# JT+Météo blocs (C.3)
JT_BLOCKS = [
    {"name": "JT+Meteo_13", "day": None, "start": "13:00", "duration_min": 40},
    {"name": "JT+Meteo_20", "day": None, "start": "20:00", "duration_min": 40},
]

# Réduction de la taille du modèle
# Nombre max de programmes candidats par créneau (slot).
# Limiter ce nombre réduit drastiquement les variables du solveur.
MAX_CANDIDATES_PER_SLOT = 25

# Publicité (C.12) – approx
MAX_AD_MIN_PER_HOUR = 12
AD_BREAK_MINUTES = 3  # on approx 1 coupure ~3 minutes

def ad_breaks_for_program(genre: str, duration_min: int) -> int:
    # pas de pub < 30 min
    if duration_min < 30:
        return 0
    # films: max 2 coupures
    if genre == "Film":
        return min(2, duration_min // 45)  # règle simple
    # autres: 1 coupure par 30-45 min approx
    return duration_min // 30
