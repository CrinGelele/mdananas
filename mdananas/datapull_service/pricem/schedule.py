from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


MOSCOW = ZoneInfo("Europe/Moscow")
CATCHUP_MARGIN = timedelta(minutes=30)


class ScheduleError(ValueError):
    pass


@dataclass(frozen=True)
class SchedulePoint:
    id: int
    hour: int
    minute: int
    is_active: bool = True


@dataclass(frozen=True)
class Occurrence:
    schedule_id: int
    scheduled_at: datetime
    next_at: datetime
    is_active: bool

    def can_download(self, now):
        if not self.is_active or not self.scheduled_at <= now < self.next_at:
            return False
        # A regular start is allowed even for intervals shorter than 30 minutes.
        return (
            now < self.scheduled_at + timedelta(minutes=1)
            or now <= self.next_at - CATCHUP_MARGIN
        )


def current_occurrence(points, now):
    """Latest daily Priceva replacement, including disabled import points."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ScheduleError("Current time must include a timezone")
    now = now.astimezone(MOSCOW)
    seen = set()
    occurrences = []
    for point in points:
        if not 0 <= point.hour <= 23 or not 0 <= point.minute <= 59:
            raise ScheduleError(f"Invalid time in schedule #{point.id}")
        key = (point.hour, point.minute)
        if key in seen:
            raise ScheduleError(
                f"Duplicate schedule time {point.hour:02d}:{point.minute:02d}"
            )
        seen.add(key)
        for offset in (-1, 0, 1):
            day = (now + timedelta(days=offset)).date()
            dt = datetime(
                day.year, day.month, day.day, point.hour, point.minute, tzinfo=MOSCOW
            )
            occurrences.append((dt, point))
    if not occurrences:
        return None
    occurrences.sort(key=lambda item: item[0])
    previous = max(
        (item for item in occurrences if item[0] <= now), key=lambda item: item[0]
    )
    next_at = min(dt for dt, _ in occurrences if dt > now)
    return Occurrence(previous[1].id, previous[0], next_at, previous[1].is_active)
