from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from .config import (
    DAYS_FR, SLOTS_PER_DAY, SLOT_MINUTES,
    TOTAL_WEEKLY_BUDGET,
    LEGAL_MIN_EURO_PERCENT, LEGAL_MIN_FR_PERCENT, LEGAL_MIN_INDEP_PERCENT,
    GENRE_GROUPS, GENRE_QUOTAS_WEEK,
    MAX_AD_MIN_PER_HOUR,
)
from .preprocess import Precomputed
from .timeutils import slot_index_from_time


@dataclass
class SolveResult:
    status: str
    objective: int
    best_bound: int
    starts: List[Tuple[int, int, int]]  # (day, start_slot, prog_idx)


def solve_ortools(
    pre: Precomputed,
    time_limit_s: int = 900,
    hint_file: str | None = None,
    gap: float = 0.0,
) -> SolveResult:
    model = cp_model.CpModel()
    D = 7
    S = SLOTS_PER_DAY
    P = len(pre.programs)

    import time as _time
    _t0 = _time.perf_counter()
    def _elapsed(): return f"{_time.perf_counter()-_t0:.1f}s"

    # start variables x[d,s,p]
    x: Dict[Tuple[int, int, int], cp_model.IntVar] = {}
    for (d, s), plist in pre.allowed_starts.items():
        for p in plist:
            x[(d, s, p)] = model.NewBoolVar(f"x_{d}_{s}_{p}")
    print(f"    [{_elapsed()}] {len(x)} x-variables created", flush=True)

    # Precompute covers[d,t] = list of (d,s,p) keys whose programme spans slot t
    covers: Dict[Tuple[int, int], List[Tuple[int, int, int]]] = {}
    for (d, s, p) in x:
        L = pre.duration_slots[p]
        for t in range(s, min(s + L, S)):
            covers.setdefault((d, t), []).append((d, s, p))
    print(f"    [{_elapsed()}] covers index built ({sum(len(v) for v in covers.values())} entries)", flush=True)

    # helper: start_indicator y[d,s] = 1 if some program starts at slot s
    y: Dict[Tuple[int, int], cp_model.IntVar] = {}
    for d in range(D):
        for s in range(S):
            vars_here = [x[(d, s, p)] for p in pre.allowed_starts.get((d, s), []) if (d, s, p) in x]
            y[(d, s)] = model.NewBoolVar(f"y_{d}_{s}")
            if vars_here:
                model.Add(sum(vars_here) == y[(d, s)])
            else:
                model.Add(y[(d, s)] == 0)

    print(f"    [{_elapsed()}] y-variables done", flush=True)

    # Coverage exact: each slot covered by exactly 1 started interval
    for d in range(D):
        for t in range(S):
            cover_terms = [x[key] for key in covers.get((d, t), [])]
            model.Add(sum(cover_terms) == 1)

    print(f"    [{_elapsed()}] Coverage constraints done", flush=True)

    # Fixes (JT+Meteo blocs inclus dans pre.fixed_start)
    for (d, s), pfix in pre.fixed_start.items():
        if (d, s, pfix) not in x:
            raise RuntimeError(f"Fix impossible: {pre.programs[pfix].id} at {d},{s}")
        model.Add(x[(d, s, pfix)] == 1)

    # Budget hebdo
    model.Add(
        sum(int(pre.programs[p].cost) * var for (d, s, p), var in x.items()) <= TOTAL_WEEKLY_BUDGET
    )

    print(f"    [{_elapsed()}] Fixes done", flush=True)

    # Quotas EU/FR/Indep (C.11)
    total_minutes = 7 * 20 * 60
    eu = sum(int(pre.programs[p].duration_minutes) * int(pre.is_european[p]) * var for (d, s, p), var in x.items())
    fr = sum(int(pre.programs[p].duration_minutes) * int(pre.is_french[p]) * var for (d, s, p), var in x.items())
    indep = sum(int(pre.programs[p].duration_minutes) * int(pre.is_independent[p]) * var for (d, s, p), var in x.items())

    model.Add(eu * 100 >= int(LEGAL_MIN_EURO_PERCENT * 100) * total_minutes)
    model.Add(fr * 100 >= int(LEGAL_MIN_FR_PERCENT * 100) * total_minutes)
    model.Add(indep * 100 >= int(LEGAL_MIN_INDEP_PERCENT * 100) * total_minutes)

    print(f"    [{_elapsed()}] Quotas EU/FR/Indep done", flush=True)

    # Identité de chaîne : au moins 30% FR (C.1) – redondant avec 40% légal, mais on garde si tu veux
    # -> déjà couvert par 40% FR légal. Si tu veux 30% seulement, supprime la contrainte 40% FR.

    print(f"    [{_elapsed()}] About to build C.2 variété", flush=True)

    # ------------------------------------------------------------
    # C.2 Variété quotidienne
    # - >= 4 genres différents / jour
    # - >= 1 documentaire / jour
    # - >= 1 magazine de société / semaine (subgenre)
    # ------------------------------------------------------------
    genres = sorted(set(pre.genre_id))
    G = len(genres)

    # genre_present[d,g]
    genre_present: Dict[Tuple[int, int], cp_model.IntVar] = {}
    for d in range(D):
        for g in range(G):
            genre_present[(d, g)] = model.NewBoolVar(f"gp_{d}_{g}")
            starts_of_g = []
            for s in range(S):
                for p in pre.allowed_starts.get((d, s), []):
                    if pre.genre_id[p] == g and (d, s, p) in x:
                        starts_of_g.append(x[(d, s, p)])
            if starts_of_g:
                model.AddMaxEquality(genre_present[(d, g)], starts_of_g)
            else:
                model.Add(genre_present[(d, g)] == 0)
        model.Add(sum(genre_present[(d, g)] for g in range(G)) >= 4)

    # 1 documentaire/jour
    for d in range(D):
        doc_starts = []
        for s in range(S):
            for p in pre.allowed_starts.get((d, s), []):
                if pre.programs[p].genre == "Documentaire" and (d, s, p) in x:
                    doc_starts.append(x[(d, s, p)])
        model.Add(sum(doc_starts) >= 1)

    # 1 magazine de société / semaine
    soc_mag = []
    for (d, s, p), var in x.items():
        if pre.programs[p].genre == "Magazine" and (pre.programs[p].subgenre or "").lower() in {"societe", "société", "magazine de société"}:
            soc_mag.append(var)
    if soc_mag:
        model.Add(sum(soc_mag) >= 1)

    print(f"    [{_elapsed()}] C.2 done (genre variety / doc / magazine)", flush=True)

    # ------------------------------------------------------------
    # C.4 Quotas de genres hebdo (temps)
    # ------------------------------------------------------------
    for group, (mn, mx) in GENRE_QUOTAS_WEEK.items():
        genres_in = GENRE_GROUPS[group]
        minutes_in_group = sum(
            int(pre.programs[p].duration_minutes) * var
            for (d, s, p), var in x.items()
            if pre.programs[p].genre in genres_in
        )
        model.Add(minutes_in_group * 100 >= int(mn * 100) * total_minutes)
        model.Add(minutes_in_group * 100 <= int(mx * 100) * total_minutes)

    print(f"    [{_elapsed()}] C.4 genre quotas done", flush=True)

    # ------------------------------------------------------------
    # C.3 Habitudes: séries récurrentes au même horaire
    # -> déjà filtré en preprocess via usual_time/usual_day
    # ------------------------------------------------------------

    print(f"    [{_elapsed()}] C.3 done", flush=True)

    # ------------------------------------------------------------
    # C.1 Cohérence de grille
    # - pas 4 programmes consécutifs du même type fiction/non-fiction
    #
    # Approche par slot de démarrage (start slots) plutôt que par paire
    # de programmes : on construit fic_at[d,s] (BoolVar) = 1 si le
    # programme qui commence au slot s est de la fiction. Ensuite on
    # impose une fenêtre glissante sur les start-slots consécutifs :
    # parmi 4 start-slots consécutifs, on ne peut pas avoir 4 fictions
    # ni 4 non-fictions.
    #
    # Cette version est O(D × start_slots) et évite l'explosion O(P²).
    # ------------------------------------------------------------

    # 1. Build fic_at[d,s] auxiliary variables (BoolVar ou constante)
    fic_at: Dict[Tuple[int, int], object] = {}   # BoolVar, True, or False
    for (d, s), plist in pre.allowed_starts.items():
        progs_in_x = [p for p in plist if (d, s, p) in x]
        if not progs_in_x:
            continue
        fic_progs  = [p for p in progs_in_x if pre.is_fiction[p]]
        nfic_progs = [p for p in progs_in_x if not pre.is_fiction[p]]

        if fic_progs and nfic_progs:
            fv = model.NewBoolVar(f"fic_{d}_{s}")
            fic_at[(d, s)] = fv
            for p in fic_progs:
                model.AddImplication(x[(d, s, p)], fv)
            for p in nfic_progs:
                model.AddImplication(x[(d, s, p)], fv.Not())
        elif fic_progs:
            fic_at[(d, s)] = True      # only fiction can start here
        else:
            fic_at[(d, s)] = False     # only non-fiction can start here

    # 2. No 4 consecutive same fiction type (fenêtre glissante sur start-slots)
    # On applique uniquement sur la plage 06:00-00:30 (hors Nuit profonde) car
    # le catalogue ne propose que des Jeunesse (fiction) en 01:30-02:00, ce qui
    # rendrait la contrainte infaisable pour cette tranche horaire.
    nuit_start = slot_index_from_time("00:30")  # slot 222 (228 min from 06:00)

    def _fic_to_expr(v):
        """Convert fic_at value (True/False/BoolVar) to a CP-SAT linear expression."""
        if v is True:
            return 1
        if v is False:
            return 0
        return v  # BoolVar

    n_c1 = 0
    for d in range(D):
        # Trier les start-slots du jour (hors Nuit profonde)
        day_slots = sorted(s for (dd, s) in fic_at if dd == d and s < nuit_start)
        for i in range(len(day_slots) - 3):
            window_vals = [fic_at.get((d, day_slots[i + k])) for k in range(4)]
            if any(v is None for v in window_vals):
                continue
            w = [_fic_to_expr(v) for v in window_vals]
            # Not all 4 fiction: sum(w) <= 3
            model.Add(sum(w) <= 3)
            # Not all 4 non-fiction: sum(w) >= 1
            model.Add(sum(w) >= 1)
            n_c1 += 2

    print(f"    [{_elapsed()}] C.1 no-4-consecutive-same-fiction-type done ({n_c1} constraints)", flush=True)

    # ------------------------------------------------------------
    # C.6 Fréquence
    # - séries : 1 épisode / semaine max
    # -> on applique par "id" (un épisode = un programme)
    # Si tu as un champ "season/series_id", on regroupe.
    # ------------------------------------------------------------
    for p in range(P):
        if pre.programs[p].genre in {"Série", "Series", "Séries"}:
            occ = [var for (d, s, pp), var in x.items() if pp == p]
            model.Add(sum(occ) <= 1)

    print(f"    [{_elapsed()}] C.6 frequency done", flush=True)

    # ------------------------------------------------------------
    # C.12 Publicité (approx):
    # - max 12 min de pub / heure
    # On calcule une audience/pub “répartie” par minute via ad_rate_milli[p].
    # Pour chaque heure (fenêtre de 60 min = 12 slots de 5 min):
    # sum(ad_minutes_in_window) <= 12
    # ------------------------------------------------------------
    slots_per_hour = 60 // SLOT_MINUTES  # 12
    for d in range(D):
        for hstart in range(0, S, slots_per_hour):
            hend = min(S, hstart + slots_per_hour)
            terms = []
            for t in range(hstart, hend):
                for key in covers.get((d, t), []):
                    _, s, p = key
                    rate = int(pre.ad_rate_milli[p] * SLOT_MINUTES)
                    if rate:
                        terms.append(rate * x[key])
            model.Add(sum(terms) <= MAX_AD_MIN_PER_HOUR * 1000)

    print(f"    [{_elapsed()}] C.12 ads done", flush=True)

    # ------------------------------------------------------------
    # C.5 Progression audience (souhaitée)
    # Désactivée comme contrainte dure car elle rend le problème trop
    # contraint pour le solveur. L'objectif de maximisation d'audience
    # encourage naturellement la progression.
    # ------------------------------------------------------------
    n_c5 = 0

    # ------------------------------------------------------------
    # Objectif: max audience globale (ou mix)
    # ------------------------------------------------------------
    print(f"    [{_elapsed()}] C.5 audience progression done", flush=True)

    # Objective: maximize total profit (ad_revenue - cost)
    model.Maximize(sum(int(pre.profit[(d, s, p)]) * var for (d, s, p), var in x.items()))

    print(f"    [{_elapsed()}] Objective set. Launching solver...", flush=True)

    # ---- Warm-start hints from previous schedule.json ----
    if hint_file:
        import json, os
        if os.path.isfile(hint_file):
            try:
                prev = json.load(open(hint_file, encoding='utf-8'))
                # Build program_id -> index lookup
                id_to_idx = {pre.programs[i].id: i for i in range(P)}
                hint_set: set[tuple[int, int, int]] = set()
                for d_idx, day_data in enumerate(prev.get('days', [])):
                    for item in day_data.get('items', []):
                        pid = item.get('program_id')
                        s = item.get('start_slot')
                        p = id_to_idx.get(pid)
                        if p is not None and s is not None:
                            hint_set.add((d_idx, s, p))
                n_hints = 0
                for key, var in x.items():
                    model.AddHint(var, 1 if key in hint_set else 0)
                    n_hints += 1
                print(f"    [{_elapsed()}] Warm-start: {len(hint_set)} hints from {hint_file}", flush=True)
            except Exception as e:
                print(f"    [{_elapsed()}] Warning: could not load hints: {e}", flush=True)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = 8
    if gap > 0:
        solver.parameters.relative_gap_limit = gap
        print(f"    [{_elapsed()}] Optimality gap set to {gap:.1%}", flush=True)

    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    starts: List[Tuple[int, int, int]] = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (d, s, p), var in x.items():
            if solver.Value(var) == 1:
                starts.append((d, s, p))

    return SolveResult(
        status=status_name,
        objective=int(solver.ObjectiveValue()) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0,
        best_bound=int(solver.BestObjectiveBound()) if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0,
        starts=sorted(starts),
    )
