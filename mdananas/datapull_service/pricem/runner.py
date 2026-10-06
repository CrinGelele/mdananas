import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

import requests
from django.conf import settings
from django.db import OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from datapull_service.models.pricem_models import (
    PricemImportRun,
    PricemLOG,
    TaskSchedule,
)

from .errors import ImportConfigurationError, PayloadError, safe_error
from .locking import assert_import_lock, import_lock
from .payload import normalize_payload
from .schedule import MOSCOW, SchedulePoint, current_occurrence
from .store import DB, persist_payload


AUTOMATIC_STATES = ("pending", "running", "retry")


@dataclass
class TickResult:
    status: str
    message: str
    run_id: int | None = None


def slot_label(run):
    return run.scheduled_at.astimezone(MOSCOW).strftime("%Y-%m-%d %H:%M MSK")


def log_run(run, status):
    PricemLOG.objects.using(DB).create(
        date_time=timezone.now(),
        schedule_id=run.schedule_id,
        status=f"{status}; slot={slot_label(run)}; run={run.pk}; attempt={run.attempts}",
    )


def retryable(error):
    if isinstance(
        error, (requests.Timeout, requests.ConnectionError, OperationalError)
    ):
        return True
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return error.response.status_code == 429 or error.response.status_code >= 500
    return False


def start_attempt(run, force=False):
    assert_import_lock()
    delays = settings.PRICEM_RETRY_DELAYS
    if not force and run.attempts >= len(delays) + 1:
        run.status = "failed"
        run.last_error = "Automatic attempt limit reached; use pricem_run --retry-run"
        run.save(using=DB, update_fields=["status", "last_error"])
        return False
    run.attempts += 1
    run.status = "running"
    run.started_at = timezone.now()
    run.finished_at = None
    run.next_retry_at = None
    run.save(
        using=DB,
        update_fields=[
            "attempts",
            "status",
            "started_at",
            "finished_at",
            "next_retry_at",
        ],
    )
    return True


def fail_attempt(run, error):
    assert_import_lock()
    # A lost response to COMMIT must not turn an already committed success into a failure.
    run.refresh_from_db(using=DB)
    if run.status == "succeeded":
        return TickResult(
            "succeeded", f"Already committed: {slot_label(run)}; {run.counts}", run.pk
        )
    run.last_error = safe_error(error)
    run.finished_at = timezone.now()
    delays = settings.PRICEM_RETRY_DELAYS
    if retryable(error) and run.attempts <= len(delays):
        run.status = "retry"
        run.next_retry_at = run.finished_at + timedelta(
            seconds=delays[run.attempts - 1]
        )
    else:
        run.status = "failed"
        run.next_retry_at = None
    run.save(
        using=DB, update_fields=["last_error", "finished_at", "status", "next_retry_at"]
    )
    log_run(run, f"{run.status}: {run.last_error}")
    return TickResult(run.status, f"{slot_label(run)}: {run.last_error}", run.pk)


def capture_snapshot(run, occurrence, force=False):
    if not start_attempt(run, force):
        return TickResult("failed", run.last_error, run.pk)
    try:
        # Recheck immediately before sending a request, not only at tick start.
        if not occurrence.can_download(timezone.now()):
            run.status = "missed"
            run.last_error = "Download window closed before the API request"
            run.save(using=DB, update_fields=["status", "last_error"])
            log_run(run, "missed: download window closed")
            return TickResult("missed", run.last_error, run.pk)
        response = requests.post(settings.PRICEVA_EXPORT_URL, timeout=(10, 120))
        response.raise_for_status()
        fetched_at = timezone.now()
        if fetched_at >= occurrence.next_at:
            # We cannot know which export was returned across a replacement boundary.
            run.status = "missed"
            run.last_error = (
                "API response crossed the next Priceva replacement; snapshot discarded"
            )
            run.save(using=DB, update_fields=["status", "last_error"])
            log_run(run, "missed: response crossed next slot")
            return TickResult("missed", run.last_error, run.pk)
        payload = response.text
        assert_import_lock()
        run.payload = payload
        run.payload_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        run.fetched_at = fetched_at
        run.status = "pending"
        run.save(
            using=DB, update_fields=["payload", "payload_hash", "fetched_at", "status"]
        )
    except Exception as error:
        return fail_attempt(run, error)
    return None


def import_snapshot(run, already_started=False, force=False):
    if not already_started and not start_attempt(run, force):
        return TickResult("failed", run.last_error, run.pk)
    if already_started:
        assert_import_lock()
        run.status = "running"
        run.save(using=DB, update_fields=["status"])
    try:
        if hashlib.sha256(run.payload.encode("utf-8")).hexdigest() != run.payload_hash:
            raise PayloadError("Saved snapshot checksum does not match")
        products = normalize_payload(run.payload)
        assert_import_lock()
        with transaction.atomic(using=DB):
            counts = persist_payload(products, run.scheduled_at)
            run.status = "succeeded"
            run.counts = json.dumps(counts, sort_keys=True)
            run.finished_at = timezone.now()
            run.last_error = ""
            run.next_retry_at = None
            run.save(
                using=DB,
                update_fields=[
                    "status",
                    "counts",
                    "finished_at",
                    "last_error",
                    "next_retry_at",
                ],
            )
            log_run(run, f"success: {run.counts}")
    except Exception as error:
        return fail_attempt(run, error)
    return TickResult("succeeded", f"Imported {slot_label(run)}: {run.counts}", run.pk)


def read_occurrence(now):
    points = [
        SchedulePoint(row["id"], row["time_hour"], row["time_minute"], row["is_active"])
        for row in TaskSchedule.objects.using(DB).values(
            "id", "time_hour", "time_minute", "is_active"
        )
    ]
    return current_occurrence(points, now)


def describe_tick(now):
    occurrence = read_occurrence(now)
    if occurrence is None:
        return TickResult("idle", "Schedule is empty")
    run = (
        PricemImportRun.objects.using(DB)
        .filter(scheduled_at=occurrence.scheduled_at)
        .first()
    )
    status = run.status if run else "not started"
    label = occurrence.scheduled_at.strftime("%Y-%m-%d %H:%M MSK")
    message = (
        f"Slot {label}; state={status}; next={occurrence.next_at:%Y-%m-%d %H:%M}; "
    )
    message += (
        "download allowed"
        if occurrence.can_download(now)
        else "download unavailable (disabled or cutoff)"
    )
    return TickResult("check", message, run.pk if run else None)


def run_tick(now=None, retry_run_id=None, check_only=False):
    now = now or timezone.now()
    if check_only:
        return describe_tick(now)
    with import_lock() as acquired:
        if not acquired:
            return TickResult("busy", "Another process is importing Priceva")
        occurrence = read_occurrence(now)
        assert_import_lock()
        fresh_id = None
        forced = None
        if retry_run_id is not None:
            forced = PricemImportRun.objects.using(DB).get(pk=retry_run_id)
            if forced.status == "succeeded":
                return TickResult(
                    "succeeded", f"Already imported {slot_label(forced)}", forced.pk
                )
            if forced.payload:
                return import_snapshot(forced, force=True)
            if (
                occurrence is None
                or forced.scheduled_at != occurrence.scheduled_at
                or not occurrence.can_download(now)
            ):
                raise ImportConfigurationError(
                    "This run has no snapshot and its Priceva download window is closed"
                )

        unfetched = (
            PricemImportRun.objects.using(DB)
            .filter(status__in=AUTOMATIC_STATES, scheduled_at__lte=now)
            .filter(Q(payload=None) | Q(payload=""))
        )
        for old in unfetched:
            if (
                occurrence is None
                or old.scheduled_at != occurrence.scheduled_at
                or not occurrence.can_download(now)
            ):
                old.status = "missed"
                old.last_error = (
                    "No snapshot was captured before the download window closed"
                )
                old.save(using=DB, update_fields=["status", "last_error"])
                log_run(old, "missed: no saved snapshot")

        # Capture the currently available export before recovering older snapshots.
        if occurrence and occurrence.can_download(now):
            current, _ = PricemImportRun.objects.using(DB).get_or_create(
                scheduled_at=occurrence.scheduled_at,
                defaults={
                    "schedule_id": occurrence.schedule_id,
                    "next_at": occurrence.next_at,
                },
            )
            ready = current.status in AUTOMATIC_STATES and (
                current.next_retry_at is None or current.next_retry_at <= now
            )
            if not current.payload and (ready or forced is not None):
                result = capture_snapshot(current, occurrence, force=forced is not None)
                if result is not None:
                    return result
                fresh_id = current.pk

        saved = (
            PricemImportRun.objects.using(DB)
            .filter(status__in=AUTOMATIC_STATES, scheduled_at__lte=now)
            .exclude(payload=None)
            .exclude(payload="")
            .filter(Q(next_retry_at=None) | Q(next_retry_at__lte=now))
            .order_by("scheduled_at")
            .first()
        )
        if saved:
            return import_snapshot(saved, already_started=saved.pk == fresh_id)
        return TickResult("idle", "No import is due; completed slots are not repeated")
