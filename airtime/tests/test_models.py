"""Tests unitaires AIRTIME — unittest (sans pytest)"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from datetime import date

from src.models import Program, Schedule, ScheduledItem
from src.audience import compute_audience
from src.revenue import compute_revenue, compute_profit, nb_pub_screens
from src.constraints import check_rerun_allowed, check_slot_allowed, check_unique_per_week, check_slot_fits
from src.loader import load_programs, _fix_encoding


def make_program(**kwargs):
    defaults = dict(
        id="TEST_001", title="Test", genre="Film", subgenre="Action",
        duration_minutes=90, cost=100_000, base_audience=2_000_000,
        origin="France", year=2023, age_rating="Tout public",
        target_audience=["Grand public"], first_broadcast=True,
        last_broadcast_date=None, min_rerun_days=30,
        preferred_slots=["Prime Time"], forbidden_slots=["Nuit"],
        compatible_genres=["Film"], incompatible_genres=["Jeunesse"],
    )
    defaults.update(kwargs)
    return Program(**defaults)


class TestProgram(unittest.TestCase):
    def test_slots_15min(self): self.assertEqual(make_program(duration_minutes=90).slots_15min, 6)
    def test_slots_15min_round(self): self.assertEqual(make_program(duration_minutes=32).slots_15min, 3)
    def test_is_series_false(self): self.assertFalse(make_program().is_series())
    def test_is_series_true(self): self.assertTrue(make_program(episode=3, season=1, total_episodes=10).is_series())
    def test_is_fixed_false(self): self.assertFalse(make_program().is_fixed())
    def test_is_fixed_true(self): self.assertTrue(make_program(fixed_time="13:00", fixed_days=["Lundi"]).is_fixed())

class TestScheduledItem(unittest.TestCase):
    def _item(self, dur=90, start=1200):
        return ScheduledItem(make_program(duration_minutes=dur), "Lundi", "Prime Time", start, 0, 0, 0)
    def test_start_str(self): self.assertEqual(self._item().start_time_str, "20:00")
    def test_end_min(self): self.assertEqual(self._item(90).end_minutes, 1290)
    def test_end_str(self): self.assertEqual(self._item(30).end_time_str, "20:30")

class TestSchedule(unittest.TestCase):
    def test_empty(self): s = Schedule(); self.assertEqual(s.total_profit, 0.0)
    def test_profit(self):
        s = Schedule(items=[ScheduledItem(make_program(), "Lundi", "Prime Time", 1200, 0, 0, 25_000)])
        self.assertEqual(s.total_profit, 25_000)
    def test_by_day(self):
        i1 = ScheduledItem(make_program(), "Lundi", "Prime Time", 1200, 0, 0, 0)
        i2 = ScheduledItem(make_program(), "Mardi", "Midi", 720, 0, 0, 0)
        s = Schedule(items=[i1, i2])
        self.assertEqual(len(s.by_day("Lundi")), 1)

class TestAudience(unittest.TestCase):
    def test_prime_preferred(self):
        p = make_program(base_audience=1_000_000, preferred_slots=["Prime Time"])
        aud = compute_audience(p, "Prime Time", "Lundi")
        self.assertAlmostEqual(aud, 1_000_000 * 1.3 * 1.05, places=0)
    def test_nuit_low(self):
        p = make_program(base_audience=1_000_000, preferred_slots=[])
        self.assertLess(compute_audience(p, "Nuit", "Lundi"), 400_000)
    def test_dimanche_bonus(self):
        p = make_program(base_audience=1_000_000, preferred_slots=[])
        self.assertGreater(compute_audience(p, "Midi", "Dimanche"), compute_audience(p, "Midi", "Lundi"))

class TestRevenue(unittest.TestCase):
    def test_screens_30(self): self.assertEqual(nb_pub_screens(30), 3)
    def test_screens_90(self): self.assertEqual(nb_pub_screens(90), 9)
    def test_rev_positive(self): self.assertGreater(compute_revenue(2_000_000, "Prime Time", 90), 0)
    def test_profit_neg(self): self.assertLess(compute_profit(10_000, 1_000_000), 0)
    def test_profit_calc(self): self.assertAlmostEqual(compute_profit(500_000, 300_000), 200_000)

class TestConstraints(unittest.TestCase):
    def test_no_date_ok(self): self.assertTrue(check_rerun_allowed(make_program(), "Lundi"))
    def test_too_recent(self):
        p = make_program(last_broadcast_date=date(2026, 2, 10), min_rerun_days=30)
        self.assertFalse(check_rerun_allowed(p, "Lundi"))
    def test_enough_delay(self):
        p = make_program(last_broadcast_date=date(2025, 12, 1), min_rerun_days=30)
        self.assertTrue(check_rerun_allowed(p, "Lundi"))
    def test_slot_forbidden(self): self.assertFalse(check_slot_allowed(make_program(forbidden_slots=["Nuit"]), "Nuit"))
    def test_slot_ok(self): self.assertTrue(check_slot_allowed(make_program(forbidden_slots=["Nuit"]), "Prime Time"))
    def test_unique_used(self): self.assertFalse(check_unique_per_week(make_program(id="X"), {"X"}))
    def test_unique_free(self): self.assertTrue(check_unique_per_week(make_program(id="X"), set()))
    def test_fits(self): self.assertTrue(check_slot_fits(1200, 1350, 90, 1200))
    def test_no_fit(self): self.assertFalse(check_slot_fits(1200, 1290, 91, 1200))

class TestLoader(unittest.TestCase):
    def test_fix_encoding(self): self.assertEqual(_fix_encoding("MatinÃ©e"), "Matinée")
    def test_count(self): self.assertEqual(len(load_programs("data/programs.json")), 200)
    def test_all_ids(self): self.assertTrue(all(p.id for p in load_programs("data/programs.json")))
    def test_no_bad_encoding(self):
        bad = [p.title for p in load_programs("data/programs.json") if "Ã" in p.title]
        self.assertEqual(bad, [])

if __name__ == "__main__":
    unittest.main(verbosity=2)
