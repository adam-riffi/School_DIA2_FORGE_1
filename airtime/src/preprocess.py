from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Tuple

from .config import (
    DAYS_FR, SLOTS_PER_DAY, SLOT_MINUTES, TIME_BANDS, DAY_COEFF,
    AGE_MIN_TIME, EUROPE_ORIGINS,
    FICTION_GENRES, NONFICTION_GENRES,
    JT_BLOCKS,
    GENRE_GROUPS, GENRE_QUOTAS_WEEK,
    MAX_AD_MIN_PER_HOUR, AD_BREAK_MINUTES, ad_breaks_for_program,
    MAX_CANDIDATES_PER_SLOT,
)
from .loader import Program
from .timeutils import slot_index_from_time, time_from_slot_index


@dataclass(frozen=True)
class Precomputed:
    programs: List[Program]
    prog_index: Dict[str, int]
    duration_slots: List[int]
    is_european: List[int]
    is_french: List[int]
    is_independent: List[int]

    genre_name: List[str]
    genre_id: List[int]
    is_fiction: List[int]

    fixed_start: Dict[Tuple[int, int], int]  # (day, slot) -> prog_idx
    allowed_starts: Dict[Tuple[int, int], List[int]]

    score: Dict[Tuple[int, int, int], int]
    audience: Dict[Tuple[int, int, int], int]     # audience at (d,s,p) based on band at s
    profit: Dict[Tuple[int, int, int], int]        # ad_revenue - cost at (d,s,p)

    ad_rate_milli: List[int]  # milli-minutes per minute (ad_min*1000/dur)


def _band_for_slot(slot: int) -> Dict:
    t = time_from_slot_index(slot)
    for b in TIME_BANDS:
        s = slot_index_from_time(b["start"])
        e = slot_index_from_time(b["end"])
        if s <= slot < e:
            return b
    return TIME_BANDS[0]


def _min_start_slot_for_age(age_rating: str) -> int:
    if age_rating in AGE_MIN_TIME:
        return slot_index_from_time(AGE_MIN_TIME[age_rating])
    return 0


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _available(p: Program, week_start: date) -> bool:
    if p.in_production:
        return False
    if p.rights_start and week_start < _parse_date(p.rights_start):
        return False
    if p.rights_end and week_start > _parse_date(p.rights_end):
        return False
    return True


def _passes_rerun_rule(p: Program, week_start: date) -> bool:
    # C.6 : Films 90j, Documentaires 30j, Séries 1 ep/semaine max (géré en contrainte)
    # Si min_rerun_days est explicitement renseigné dans les données, il prend la priorité.
    # Sinon, on applique les règles par défaut par genre.
    genre = p.genre
    min_days = p.min_rerun_days
    if min_days is None:
        if genre == "Film":
            min_days = 90
        elif genre == "Documentaire":
            min_days = 30
        elif genre in {"JT", "Actualités", "News"}:
            # Les journaux télévisés et actualités se diffusent chaque jour / chaque semaine
            min_days = 1
        # Pour Séries, Magazine, Sport, Jeunesse, Divertissement :
        # pas de règle de délai fixe par défaut (géré au cas par cas via min_rerun_days dans les données)

    if not p.last_broadcast_date or not min_days:
        return True
    try:
        last = _parse_date(p.last_broadcast_date)
    except ValueError:
        return True
    return (week_start - last).days >= int(min_days)


def build_precomputed(programs: List[Program], week_start: date) -> Precomputed:
    # On injecte 2 “pseudo-programmes” JT+Météo fixes (C.3)
    injected = []
    for b in JT_BLOCKS:
        injected.append(Program(
            id=b["name"],
            title=b["name"].replace("_", " "),
            genre="JT",
            subgenre="JT+Météo",
            duration_minutes=b["duration_min"],
            cost=0,
            base_audience=800_000,
            origin="France",
            year=2026,
            age_rating="Tout public",
            fixed_time=b["start"],
            fixed_days=DAYS_FR,  # tous les jours
        ))
    programs = programs + injected

    prog_index = {p.id: i for i, p in enumerate(programs)}
    duration_slots: List[int] = []
    is_european: List[int] = []
    is_french: List[int] = []
    is_independent: List[int] = []
    genre_name: List[str] = []
    genre_id: List[int] = []
    is_fiction: List[int] = []

    # genre ids
    uniq_genres = sorted({p.genre for p in programs})
    gmap = {g: k for k, g in enumerate(uniq_genres)}

    fixed_start: Dict[Tuple[int, int], int] = {}

    ad_rate_milli: List[int] = []

    for i, p in enumerate(programs):
        # slots
        slots = (p.duration_minutes + SLOT_MINUTES - 1) // SLOT_MINUTES
        duration_slots.append(slots)

        fr = 1 if (p.origin or "").lower() == "france" else 0
        is_french.append(fr)
        eu = 1 if (p.origin in EUROPE_ORIGINS or fr == 1) else 0
        is_european.append(eu)

        indep = 1 if (p.independent is True) else 0
        is_independent.append(indep)

        genre_name.append(p.genre)
        genre_id.append(gmap[p.genre])
        is_fiction.append(1 if (p.genre in FICTION_GENRES) else 0)

        # ads rate (milli-minutes per minute)
        breaks = ad_breaks_for_program(p.genre, p.duration_minutes)
        ad_min_total = breaks * AD_BREAK_MINUTES
        if p.duration_minutes > 0:
            ad_rate_milli.append(int(ad_min_total * 1000 / p.duration_minutes))
        else:
            ad_rate_milli.append(0)

        # fixes
        if p.fixed_time and p.fixed_days:
            s = slot_index_from_time(p.fixed_time)
            for dname in p.fixed_days:
                if dname in DAYS_FR:
                    d = DAYS_FR.index(dname)
                    fixed_start[(d, s)] = i

    allowed_starts: Dict[Tuple[int, int], List[int]] = {}
    score: Dict[Tuple[int, int, int], int] = {}
    audience: Dict[Tuple[int, int, int], int] = {}
    profit: Dict[Tuple[int, int, int], int] = {}

    for d, dname in enumerate(DAYS_FR):
        day_coeff = DAY_COEFF[dname]
        for s in range(SLOTS_PER_DAY):
            key = (d, s)
            band = _band_for_slot(s)
            plist: List[int] = []
            for i, p in enumerate(programs):
                L = duration_slots[i]
                if s + L > SLOTS_PER_DAY:
                    continue

                # disponibilité (C.14)
                if not _available(p, week_start):
                    continue

                # rerun (C.6)
                if not _passes_rerun_rule(p, week_start):
                    continue

                # signalétique (C.10)
                if s < _min_start_slot_for_age(p.age_rating):
                    continue

                # nouveautés (C.7) : Access Prime / Prime obligatoire
                if p.is_new:
                    access_s = slot_index_from_time("18:00")
                    prime_e = slot_index_from_time("22:30")
                    if not (access_s <= s < prime_e):
                        continue

                # exclusivités (C.7) : 6 mois ~ 180 jours
                if p.is_exclusive and p.last_broadcast_date:
                    try:
                        last = _parse_date(p.last_broadcast_date)
                        if (week_start - last).days < 180:
                            continue
                    except Exception:
                        pass

                # séries récurrentes au même horaire (C.3)
                # On tolère une plage de ±4 slots (±20 min) autour de l'horaire habituel
                # pour éviter le sur-contraignement lorsque plusieurs séries sont
                # assignées au même créneau exact dans le catalogue.
                if p.genre in {"Série", "Series", "Séries"} and p.usual_time:
                    usual_s = slot_index_from_time(p.usual_time)
                    if not (usual_s - 4 <= s <= usual_s + 4):
                        continue
                    if p.usual_day and p.usual_day in DAYS_FR and d != DAYS_FR.index(p.usual_day):
                        continue

                plist.append(i)

                aud = int(p.base_audience * band["aud_mult"] * day_coeff)
                # Ad revenue estimate
                breaks = ad_breaks_for_program(p.genre, p.duration_minutes)
                ad_min = breaks * AD_BREAK_MINUTES
                revenue = int(aud / 1000 * band["cpm"] * ad_min)
                prog_profit = revenue - int(p.cost)

                score[(d, s, i)] = aud
                audience[(d, s, i)] = aud
                profit[(d, s, i)] = prog_profit

            # Limiter les candidats par slot pour réduire la taille du modèle
            # Sélection diversifiée par genre + coût pour maintenir la faisabilité
            if len(plist) > MAX_CANDIDATES_PER_SLOT:
                fixed_p = fixed_start.get(key)
                # Regrouper par genre
                from collections import defaultdict
                by_genre: dict[str, list] = defaultdict(list)
                for i in plist:
                    by_genre[programs[i].genre].append(i)

                kept_set: set[int] = set()

                for g in by_genre:
                    # Garder le meilleur par audience ET le moins cher par genre
                    by_score = sorted(by_genre[g], key=lambda i: score.get((d, s, i), 0), reverse=True)
                    by_cost = sorted(by_genre[g], key=lambda i: programs[i].cost)
                    kept_set.add(by_score[0])  # meilleur audience
                    kept_set.add(by_cost[0])   # moins cher
                    if len(by_score) > 1:
                        kept_set.add(by_score[1])  # 2e meilleur audience

                # Remplir le reste par score global
                remaining = sorted(
                    [i for i in plist if i not in kept_set],
                    key=lambda i: score.get((d, s, i), 0), reverse=True
                )
                for i in remaining:
                    if len(kept_set) >= MAX_CANDIDATES_PER_SLOT:
                        break
                    kept_set.add(i)
                # Ajouter le programme fixe si nécessaire
                if fixed_p is not None:
                    kept_set.add(fixed_p)
                new_plist = [i for i in plist if i in kept_set]
                # Nettoyer les scores des programmes exclus
                for i in plist:
                    if i not in kept_set:
                        score.pop((d, s, i), None)
                        audience.pop((d, s, i), None)
                        profit.pop((d, s, i), None)
                plist = new_plist

            allowed_starts[key] = plist

    return Precomputed(
        programs=programs,
        prog_index=prog_index,
        duration_slots=duration_slots,
        is_european=is_european,
        is_french=is_french,
        is_independent=is_independent,
        genre_name=genre_name,
        genre_id=genre_id,
        is_fiction=is_fiction,
        fixed_start=fixed_start,
        allowed_starts=allowed_starts,
        score=score,
        audience=audience,
        profit=profit,
        ad_rate_milli=ad_rate_milli,
    )
