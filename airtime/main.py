from __future__ import annotations

import argparse
import json
from datetime import date, timedelta

from src.loader import load_programs
from src.preprocess import build_precomputed
from src.ortools_solver import solve_ortools
from src.minizinc_solver import solve_minizinc
from src.export import starts_to_schedule


def next_monday(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--programs", default="data/programs.json")
    ap.add_argument("--solver", choices=["ortools", "minizinc"], default="ortools")
    ap.add_argument("--time-limit", type=int, default=600)
    ap.add_argument("--hint", default="schedule.json", help="Path to previous schedule.json for warm-start (auto-skipped if missing)")
    ap.add_argument("--gap", type=float, default=0.001, help="Relative optimality gap (e.g. 0.01 = 1%%)")
    ap.add_argument("--week-start", default=None, help="YYYY-MM-DD (défaut: lundi prochain)")
    ap.add_argument("--out", default="schedule.json")
    args = ap.parse_args()

    print("[1] Loading programs...", flush=True)
    programs = load_programs(args.programs)
    print(f"    {len(programs)} programs loaded.", flush=True)

    if args.week_start:
        y, m, d = map(int, args.week_start.split("-"))
        ws = date(y, m, d)
    else:
        ws = next_monday(date.today())

    print(f"[2] Building precomputed (week_start={ws})...", flush=True)
    pre = build_precomputed(programs, ws)
    print(f"    {len(pre.allowed_starts)} allowed-start slots, {sum(len(v) for v in pre.allowed_starts.values())} total entries.", flush=True)

    print(f"[3] Solving with {args.solver} (limit={args.time_limit}s)...", flush=True)
    if args.solver == "ortools":
        res = solve_ortools(pre, time_limit_s=args.time_limit, hint_file=args.hint, gap=args.gap)
        starts = res.starts
        meta = {"solver": "ortools", "status": res.status, "objective": res.objective, "best_bound": res.best_bound, "week_start": str(ws)}
    else:
        res = solve_minizinc(pre, model_path="src/minizinc_model.mzn", workdir="mzn_work", timeout_s=args.time_limit)
        starts = res.starts
        meta = {"solver": "minizinc", "status": res.status, "objective": res.objective, "week_start": str(ws)}

    sched = starts_to_schedule(pre, starts)
    sched["meta"] = meta

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(sched, f, ensure_ascii=False, indent=2)

    print(f"Written: {args.out}")
    print(meta)


if __name__ == "__main__":
    main()
