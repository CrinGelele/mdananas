from datetime import datetime, timedelta, timezone
import unittest

import tests  # noqa: F401 -- adds the Django project directory to sys.path
from datapull_service.pricem.schedule import (
    MOSCOW,
    ScheduleError,
    SchedulePoint,
    current_occurrence,
)


def at(hour, minute=0, day=6, second=0):
    return datetime(2026, 10, day, hour, minute, second, tzinfo=MOSCOW)


class ScheduleTests(unittest.TestCase):
    points = [SchedulePoint(1, 9, 30), SchedulePoint(2, 14, 15)]

    def test_catchup_and_exact_cutoff(self):
        slot = current_occurrence(self.points, at(11, 10))
        self.assertEqual(slot.scheduled_at, at(9, 30))
        self.assertEqual(slot.next_at, at(14, 15))
        self.assertTrue(slot.can_download(at(13, 45)))
        self.assertFalse(slot.can_download(at(13, 45, second=1)))

    def test_midnight_uses_previous_date(self):
        slot = current_occurrence(self.points, at(1))
        self.assertEqual(slot.scheduled_at, at(14, 15, day=5))
        self.assertEqual(slot.next_at, at(9, 30))
        self.assertTrue(slot.can_download(at(1)))

    def test_exact_point_selects_new_occurrence(self):
        slot = current_occurrence(self.points, at(14, 15))
        self.assertEqual(slot.schedule_id, 2)
        self.assertTrue(slot.can_download(at(14, 15)))

    def test_disabled_point_is_still_a_replacement_boundary(self):
        points = [SchedulePoint(1, 9, 30), SchedulePoint(2, 14, 15, False)]
        self.assertFalse(
            current_occurrence(points, at(14, 16)).can_download(at(14, 16))
        )
        self.assertFalse(current_occurrence(points, at(14)).can_download(at(14)))

    def test_one_daily_point_wraps_to_next_day(self):
        slot = current_occurrence(self.points[:1], at(10))
        self.assertEqual(slot.next_at - slot.scheduled_at, timedelta(days=1))

    def test_short_interval_has_regular_start_but_no_catchup(self):
        points = [SchedulePoint(1, 9, 30), SchedulePoint(2, 9, 50)]
        slot = current_occurrence(points, at(9, 30, second=20))
        self.assertTrue(slot.can_download(at(9, 30, second=20)))
        self.assertFalse(slot.can_download(at(9, 31)))

    def test_empty_invalid_and_duplicate_schedules(self):
        self.assertIsNone(current_occurrence([], at(10)))
        with self.assertRaises(ScheduleError):
            current_occurrence([SchedulePoint(1, 24, 0)], at(10))
        with self.assertRaises(ScheduleError):
            current_occurrence([SchedulePoint(1, 9, 0), SchedulePoint(2, 9, 0)], at(10))
        with self.assertRaises(ScheduleError):
            current_occurrence(self.points, datetime(2026, 10, 6, 10))

    def test_utc_input_matches_moscow_occurrence(self):
        self.assertEqual(
            current_occurrence(
                self.points, at(10).astimezone(timezone.utc)
            ).scheduled_at,
            at(9, 30),
        )
