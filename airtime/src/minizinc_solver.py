from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple

import minizinc

from .config import DAYS_FR, SLOTS_PER_DAY, TOTAL_WEEKLY_BUDGET, LEGAL_MIN_EURO_PERCENT, LEGAL_MIN_FR_PERCENT
from .preprocess import Precomputed


@dataclass
class MznResult:
    status: str
    objective: int
    starts: List[Tuple[int, int, int]]  # (day, slot, prog_idx)


def _write_dzn(pre: Precomputed, dzn_path: str) -> None:
    D = 7
    S = SLOTS_PER_DAY
    P = len(pre.programs)

    # arrays 1-based for MiniZinc
    dur_slots = [pre.duration_slots[i] for i in range(P)]
    dur_min = [int(pre.programs[i].duration_minutes) for i in range(P)]
    cost = [int(pre.programs[i].cost) for i in range(P)]
    is_eu = [int(pre.is_european[i]) for i in range(P)]
    is_fr = [int(pre.is_french[i]) for i in range(P)]

    fixed = [[0 for _ in range(S)] for _ in range(D)]
    for (d, s), pfix in pre.fixed_start.items():
        fixed[d][s] = pfix + 1  # 1-based

    allowed = [[[False for _ in range(P)] for _ in range(S)] for _ in range(D)]
    score = [[[0 for _ in range(P)] for _ in range(S)] for _ in range(D)]

    for (d, s), plist in pre.allowed_starts.items():
        for p in plist:
            allowed[d][s][p] = True
            score[d][s][p] = int(pre.score[(d, s, p)])

    def mzn_list(xs):
        return "[" + ", ".join(str(x) for x in xs) + "]"

    # attention: tableaux multi-dim en MiniZinc => concat en array2d/array3d
    # ici on écrit littéralement avec "array3d(...)" via syntaxe [| ... |]
    lines = []
    lines += [f"D={D};", f"S={S};", f"P={P};"]
    lines += [f"weekly_budget={TOTAL_WEEKLY_BUDGET};"]
    lines += [f"total_minutes={7*20*60};"]
    lines += [f"min_eu_percent={int(LEGAL_MIN_EURO_PERCENT*100)};"]
    lines += [f"min_fr_percent={int(LEGAL_MIN_FR_PERCENT*100)};"]
    lines += [f"dur_slots={mzn_list(dur_slots)};"]
    lines += [f"dur_min={mzn_list(dur_min)};"]
    lines += [f"cost={mzn_list(cost)};"]
    lines += [f"is_eu={mzn_list(is_eu)};"]
    lines += [f"is_fr={mzn_list(is_fr)};"]

    # fixed_prog: D x S
    fixed_rows = ["| " + ", ".join(str(fixed[d][s]) for s in range(S)) for d in range(D)]
    lines += ["fixed_prog = array2d(1..D,1..S,[ " + ", ".join(str(fixed[d][s]) for d in range(D) for s in range(S)) + " ]);"]

    # allowed: D x S x P
    flat_allowed = []
    flat_score = []
    for d in range(D):
        for s in range(S):
            for p in range(P):
                flat_allowed.append("true" if allowed[d][s][p] else "false")
                flat_score.append(str(score[d][s][p]))

    lines += ["allowed = array3d(1..D,1..S,1..P,[ " + ", ".join(flat_allowed) + " ]);"]
    lines += ["score = array3d(1..D,1..S,1..P,[ " + ", ".join(flat_score) + " ]);"]

    Path(dzn_path).write_text("\n".join(lines), encoding="utf-8")


def solve_minizinc(pre: Precomputed, model_path: str, workdir: str, timeout_s: int = 60) -> MznResult:
    work = Path(workdir)
    work.mkdir(parents=True, exist_ok=True)
    dzn_path = str(work / "instance.dzn")
    _write_dzn(pre, dzn_path)

    mzn_model = minizinc.Model(model_path)
    gecode = minizinc.Solver.lookup("gecode")  # ou "chuffed" si dispo
    inst = minizinc.Instance(gecode, mzn_model)
    inst.add_file(dzn_path)

    result = inst.solve(timeout=timedelta(seconds=timeout_s))

    status = str(result.status)
    objective = int(result["obj"]) if "obj" in result else 0

    # x est D x S x P bool
    starts: List[Tuple[int, int, int]] = []
    if "x" in result:
        x = result["x"]
        for d in range(7):
            for s in range(SLOTS_PER_DAY):
                for p in range(len(pre.programs)):
                    if x[d][s][p]:
                        starts.append((d, s, p))

    return MznResult(status=status, objective=objective, starts=sorted(starts))
