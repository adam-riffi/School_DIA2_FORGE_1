int: D;
int: S;
int: P;
int: G;

set of int: DAYS = 1..D;
set of int: SLOTS = 1..S;
set of int: PROGS = 1..P;
set of int: GENRES = 1..G;

array[PROGS] of int: dur_slots;
array[PROGS] of int: dur_min;
array[PROGS] of int: cost;

array[PROGS] of int: is_eu;
array[PROGS] of int: is_fr;
array[PROGS] of int: is_indep;

array[PROGS] of int: genre_id;     % 1..G
array[PROGS] of int: is_fiction;   % 0/1

int: weekly_budget;
int: total_minutes;
int: min_eu_percent;
int: min_fr_percent;
int: min_indep_percent;

array[DAYS, SLOTS, PROGS] of bool: allowed;
array[DAYS, SLOTS] of int: fixed_prog;  % 0 if none else prog index

array[DAYS, SLOTS, PROGS] of int: aud;  % audience if start
array[PROGS] of int: ad_rate_milli;     % milli-minutes per minute

int: slot_minutes;
int: max_ad_min_per_hour;

int: access_start_slot;
int: prime_end_slot;

array[DAYS, SLOTS, PROGS] of var bool: x;

% allowed
constraint forall(d in DAYS, s in SLOTS, p in PROGS)(
  x[d,s,p] -> allowed[d,s,p]
);

% coverage
constraint forall(d in DAYS, t in SLOTS)(
  sum(s in SLOTS, p in PROGS where (s <= t /\ t < s + dur_slots[p])) (bool2int(x[d,s,p])) = 1
);

% fixes
constraint forall(d in DAYS, s in SLOTS where fixed_prog[d,s] > 0)(
  x[d,s,fixed_prog[d,s]] = true
);

% budget
constraint sum(d in DAYS, s in SLOTS, p in PROGS)(
  cost[p] * bool2int(x[d,s,p])
) <= weekly_budget;

% quotas EU/FR/INDEP
constraint
  sum(d in DAYS, s in SLOTS, p in PROGS)(dur_min[p] * is_eu[p] * bool2int(x[d,s,p])) * 100
    >= min_eu_percent * total_minutes;

constraint
  sum(d in DAYS, s in SLOTS, p in PROGS)(dur_min[p] * is_fr[p] * bool2int(x[d,s,p])) * 100
    >= min_fr_percent * total_minutes;

constraint
  sum(d in DAYS, s in SLOTS, p in PROGS)(dur_min[p] * is_indep[p] * bool2int(x[d,s,p])) * 100
    >= min_indep_percent * total_minutes;

% ---------- variété quotidienne ----------
array[DAYS, GENRES] of var 0..1: genre_present;

constraint forall(d in DAYS, g in GENRES)(
  genre_present[d,g] = min(1, sum(s in SLOTS, p in PROGS where genre_id[p]==g)(bool2int(x[d,s,p])))
);
constraint forall(d in DAYS)(
  sum(g in GENRES)(genre_present[d,g]) >= 4
);

% 1 documentaire / jour => on encode “Documentaire” via un genre_id dédié côté data
int: doc_genre_id;
constraint forall(d in DAYS)(
  sum(s in SLOTS, p in PROGS where genre_id[p]==doc_genre_id)(bool2int(x[d,s,p])) >= 1
);

% 1 magazine société / semaine (on le pré-filtre dans allowed + un flag serait mieux; ici on donne une liste)
set of int: societe_mag_programs;
constraint sum(d in DAYS, s in SLOTS, p in societe_mag_programs)(bool2int(x[d,s,p])) >= 1;

% ---------- alternance fiction / non-fiction ----------
constraint forall(d in DAYS, s in SLOTS, p1 in PROGS where allowed[d,s,p1])(
  let { int: e1 = s + dur_slots[p1] } in
    (e1 <= S) ->
    ( x[d,s,p1] ->
      sum(p2 in PROGS where allowed[d,e1,p2] /\ is_fiction[p2]==is_fiction[p1]) (bool2int(x[d,e1,p2])) = 0
    )
);

% ---------- max 3 mêmes genres consécutifs (interdit chaîne de 4) ----------
constraint forall(d in DAYS, s in SLOTS, p1 in PROGS where allowed[d,s,p1])(
  let {
    int: g = genre_id[p1],
    int: e1 = s + dur_slots[p1]
  } in
  (e1 <= S) ->
  forall(p2 in PROGS where allowed[d,e1,p2] /\ genre_id[p2]==g)(
    let { int: e2 = e1 + dur_slots[p2] } in
    (e2 <= S) ->
    forall(p3 in PROGS where allowed[d,e2,p3] /\ genre_id[p3]==g)(
      let { int: e3 = e2 + dur_slots[p3] } in
      (e3 <= S) ->
      forall(p4 in PROGS where allowed[d,e3,p4] /\ genre_id[p4]==g)(
        bool2int(x[d,s,p1]) + bool2int(x[d,e1,p2]) + bool2int(x[d,e2,p3]) + bool2int(x[d,e3,p4]) <= 3
      )
    )
  )
);

% ---------- publicité (approx) max 12min / heure ----------
int: slots_per_hour = 60 div slot_minutes;
constraint forall(d in DAYS, h in 1..(S div slots_per_hour))(
  let { int: hs = (h-1)*slots_per_hour + 1, int: he = h*slots_per_hour } in
  sum(t in hs..he, s in SLOTS, p in PROGS where (s <= t /\ t < s + dur_slots[p])) (
    (ad_rate_milli[p] * slot_minutes) * bool2int(x[d,s,p])
  ) <= max_ad_min_per_hour * 1000
);

% ---------- progression audience: pas de chute >30% en access+prime ----------
array[DAYS, SLOTS] of var int: aud_slot;
constraint forall(d in DAYS, t in SLOTS)(
  aud_slot[d,t] =
    sum(s in SLOTS, p in PROGS where (s <= t /\ t < s + dur_slots[p]))(aud[d,s,p] * bool2int(x[d,s,p]))
);

constraint forall(d in DAYS, t in access_start_slot..(prime_end_slot-1))(
  100 * aud_slot[d,t+1] >= 70 * aud_slot[d,t]
);

% objectif
var int: obj = sum(d in DAYS, s in SLOTS, p in PROGS)(aud[d,s,p] * bool2int(x[d,s,p]));
solve maximize obj;
