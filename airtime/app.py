import json
import streamlit as st

GENRE_COLORS = {
    "Film": "#FF6B6B",
    "Série": "#4D96FF",
    "Séries": "#4D96FF",
    "Series": "#4D96FF",
    "Documentaire": "#6BCB77",
    "Magazine": "#FFD93D",
    "Divertissement": "#FF9F1C",
    "JT": "#845EC2",
    "Actualités": "#845EC2",
    "Sport": "#00C9A7",
    "Sports": "#00C9A7",
    "Jeunesse": "#F9A8D4",
}


def fmt_euro(v: int) -> str:
    """Format integer as euro string with thousands separators."""
    return f"{v:,.0f} €".replace(",", " ")


def profit_icon(profit: int) -> str:
    return "🟢" if profit >= 0 else "🔴"


st.set_page_config(page_title="Grille TV - Semaine", layout="wide")

st.title("📺 Grille TV — Programme de la semaine")

SCHEDULE_PATH = "schedule.json"

try:
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    st.error(f"Fichier `{SCHEDULE_PATH}` introuvable. Lance `python main.py` d'abord.")
    st.stop()

meta = data.get("meta", {})

# ── Solver status & optimality ─────────────────────────────────────
solver_status = meta.get("status", "Unknown")
objective = meta.get("objective", None)
week_start = meta.get("week_start", "—")
solver_name = meta.get("solver", "—")

status_color = "🟢" if solver_status == "OPTIMAL" else "🟡" if "FEASIBLE" in str(solver_status).upper() else "🔴"

st.header("📈 Statut du solveur")
s1, s2, s3 = st.columns(3)
s1.metric("Solveur", solver_name)
s2.metric("Semaine", week_start)
s3.metric(f"{status_color} Statut", solver_status)

if objective is not None:
    gap = meta.get("gap", None)
    best_bound = meta.get("best_bound", None)
    if gap is not None:
        gap_pct = gap * 100 if gap < 1 else gap
        st.info(f"Écart à l'optimal : **{gap_pct:.2f} %** — Profit : **{objective:,.0f}** / Optimal : **{objective:,.0f}**")
    elif best_bound is not None and objective != 0:
        computed_gap = abs(objective - best_bound) / abs(objective) * 100
        st.info(f"Écart à l'optimal : **{computed_gap:.2f} %** — Profit : **{objective:,.0f}** / Optimal : **{best_bound:,.0f}**")
    else:
        gap_label = "0.00 %" if solver_status == "OPTIMAL" else "N/A"
        st.info(f"Écart à l'optimal : **{gap_label}** — Profit : **{objective:,.0f}**")

st.divider()

# ── Weekly budget summary ──────────────────────────────────────────
budget = data.get("budget_summary", {})
if budget:
    st.header("💰 Budget hebdomadaire")

    w_cost = budget.get("weekly_cost", 0)
    w_rev = budget.get("weekly_revenue", 0)
    w_profit = budget.get("weekly_profit", 0)
    w_limit = budget.get("budget_limit", 5_000_000)
    w_pct = budget.get("budget_used_pct", 0)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Coût total", fmt_euro(w_cost))
    k2.metric("Revenus pub", fmt_euro(w_rev))
    k3.metric(f"{profit_icon(w_profit)} Profit semaine", fmt_euro(w_profit))
    k4.metric("Budget utilisé", f"{w_pct} %")

    # Progress bar for budget usage
    st.progress(min(w_pct / 100, 1.0), text=f"Budget : {fmt_euro(w_cost)} / {fmt_euro(w_limit)}")
    st.divider()

# ── Daily breakdown table ──────────────────────────────────────────
days = data["days"]

has_budget_data = any("day_cost" in d for d in days)
if has_budget_data:
    st.header("📊 Récapitulatif par jour")
    cols = st.columns(7)
    for i, d in enumerate(days):
        dc = d.get("day_cost", 0)
        dr = d.get("day_revenue", 0)
        dp = d.get("day_profit", 0)
        with cols[i]:
            st.subheader(d["day"][:3])
            st.metric("Coût", fmt_euro(dc))
            st.metric("Revenus", fmt_euro(dr))
            icon = profit_icon(dp)
            color = "#22c55e" if dp >= 0 else "#ef4444"
            st.markdown(
                f"<div style='text-align:center; font-size:20px; font-weight:700; color:{color};'>"
                f"{icon} {fmt_euro(dp)}</div>",
                unsafe_allow_html=True,
            )
    st.divider()

# ── Per-day program cards ──────────────────────────────────────────
for d in days:
    day_name = d["day"]
    dc = d.get("day_cost", 0)
    dr = d.get("day_revenue", 0)
    dp = d.get("day_profit", 0)

    header_extra = ""
    if has_budget_data:
        icon = profit_icon(dp)
        header_extra = f" — {icon} Profit : {fmt_euro(dp)}"

    st.header(f"{day_name}{header_extra}")
    items = d["items"]

    if not items:
        st.warning("Aucun item.")
        continue

    for it in items:
        genre = it.get("genre", "Autre")
        color = GENRE_COLORS.get(genre, "#CBD5E1")

        start = it["start_time"]
        end = it["end_time"]
        title = it["title"]
        dur = it["duration_minutes"]
        sub = it.get("subgenre", "")

        cost = it.get("cost", 0)
        revenue = it.get("ad_revenue", 0)
        prog_profit = revenue - cost
        p_icon = profit_icon(prog_profit)
        p_color = "#22c55e" if prog_profit >= 0 else "#ef4444"

        # Build the budget line only if cost/revenue data exists
        budget_html = ""
        if "cost" in it:
            budget_html = f"""
              <div style="display:flex; gap:16px; margin-top:4px; font-size:13px;">
                <span style="color:#94a3b8;">Coût: <b>{fmt_euro(cost)}</b></span>
                <span style="color:#94a3b8;">Revenus pub: <b>{fmt_euro(revenue)}</b></span>
                <span style="color:{p_color}; font-weight:700;">{p_icon} {fmt_euro(prog_profit)}</span>
              </div>
            """

        st.markdown(
            f"""
            <div style="
                border-left: 10px solid {color};
                background: #0b1220;
                padding: 10px 12px;
                border-radius: 10px;
                margin-bottom: 8px;">
              <div style="display:flex; justify-content:space-between; gap:12px;">
                <div style="font-weight:700; font-size:16px; color:#e5e7eb;">
                  {start} → {end} • {title}
                </div>
                <div style="color:#cbd5e1; font-weight:600;">
                  {dur} min
                </div>
              </div>
              <div style="color:#9ca3af; margin-top:4px;">
                <span style="font-weight:600; color:#cbd5e1;">{genre}</span>
                {(" • " + sub) if sub else ""}
              </div>
              {budget_html}
            </div>
            """,
            unsafe_allow_html=True,
        )
