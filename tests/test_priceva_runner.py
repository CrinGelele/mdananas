from contextlib import nullcontext
from datetime import datetime, time, timedelta
import hashlib
import json
from unittest.mock import Mock, patch

import requests
from django.db import OperationalError

from tests.support import DatabaseTest, export, payload
from datapull_service.models.pricem_models import (
    PricemImportRun,
    PricemLOG,
    TaskSchedule,
    PRICEM_DATA_INT_Monitoring,
    PRICEM_DATA_Monitoring_Sources,
    PRICEM_DATA_Source_Offers,
)
from datapull_service.pricem.errors import ImportConfigurationError, PayloadError
from datapull_service.pricem.runner import run_tick
from datapull_service.pricem.schedule import MOSCOW
from datapull_service.pricem.store import persist_payload
from datapull_service.pricem.payload import normalize_payload
from root_service.models.ref_sku_models import Cu, Tu


class RunnerTests(DatabaseTest):
    def setUp(self):
        super().setUp()
        self.now = datetime(2026, 10, 6, 11, 10, tzinfo=MOSCOW)
        self.first = TaskSchedule.objects.using("ideal").create(
            time_hour=9, time_minute=30, is_active=True
        )
        self.second = TaskSchedule.objects.using("ideal").create(
            time_hour=14, time_minute=15, is_active=True
        )
        cu = Cu.objects.using("ideal").create(
            xcode_cu="CU1", category="Food", groupname="Group", brand="OWN"
        )
        self.tu = Tu.objects.using("ideal").create(
            xcode_tu="TU1", root_cu=cu, status="ACT", type="A", cu_in_tu=10
        )
        self.lock = patch(
            "datapull_service.pricem.runner.import_lock", return_value=nullcontext(True)
        )
        self.lock.start()
        self.addCleanup(self.lock.stop)
        self.assert_lock = patch("datapull_service.pricem.runner.assert_import_lock")
        self.assert_lock.start()
        self.addCleanup(self.assert_lock.stop)
        self.clock = patch(
            "datapull_service.pricem.runner.timezone.now", side_effect=lambda: self.now
        )
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.api = patch("datapull_service.pricem.runner.requests.post")
        self.post = self.api.start()
        self.addCleanup(self.api.stop)
        self.post.return_value = Mock(text=payload(), raise_for_status=Mock())

    def tick(self, **kwargs):
        return run_tick(now=self.now, **kwargs)

    def test_catchup_uses_scheduled_date_and_minutes_and_is_not_repeated(self):
        result = self.tick()
        self.assertEqual(result.status, "succeeded")
        offer = PRICEM_DATA_Source_Offers.objects.using("ideal").get()
        self.assertEqual(offer.upload_date, self.now.date())
        self.assertEqual(offer.upload_time, time(9, 30))
        self.assertEqual(offer.offer, "")
        self.assertEqual(self.tick().status, "idle")
        self.post.assert_called_once()
        self.assertEqual(
            PricemImportRun.objects.using("ideal").get().status, "succeeded"
        )
        self.assertEqual(PricemLOG.objects.using("ideal").count(), 1)

    def test_midnight_preserves_previous_day(self):
        self.now = datetime(2026, 10, 7, 1, tzinfo=MOSCOW)
        self.assertEqual(self.tick().status, "succeeded")
        offer = PRICEM_DATA_Source_Offers.objects.using("ideal").get()
        self.assertEqual(str(offer.upload_date), "2026-10-06")
        self.assertEqual(offer.upload_time, time(14, 15))

    def test_no_api_call_inside_cutoff(self):
        self.now = self.now.replace(hour=13, minute=45, second=1)
        self.assertEqual(self.tick().status, "idle")
        self.post.assert_not_called()
        self.assertEqual(PricemImportRun.objects.using("ideal").count(), 0)

    def test_busy_lock_makes_no_writes_or_api_call(self):
        with patch(
            "datapull_service.pricem.runner.import_lock",
            return_value=nullcontext(False),
        ):
            self.assertEqual(self.tick().status, "busy")
        self.post.assert_not_called()
        self.assertEqual(PricemImportRun.objects.using("ideal").count(), 0)

    def test_transaction_rollback_and_retry_same_snapshot_after_replacement(self):
        def crash(products, scheduled_at):
            persist_payload(products, scheduled_at)
            raise OperationalError("simulated failure after writing prices")

        with patch("datapull_service.pricem.runner.persist_payload", side_effect=crash):
            self.assertEqual(self.tick().status, "retry")
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 0)
        run = PricemImportRun.objects.using("ideal").get()
        self.assertTrue(run.payload)
        self.now = self.now.replace(hour=14, minute=16)
        self.second.is_active = False
        self.second.save(using="ideal")
        self.assertEqual(self.tick().status, "succeeded")
        self.post.assert_called_once()
        offer = PRICEM_DATA_Source_Offers.objects.using("ideal").get()
        self.assertEqual(offer.upload_time, time(9, 30))

    def test_network_retry_waits_and_expired_unfetched_run_is_missed(self):
        self.post.side_effect = requests.Timeout("network timeout")
        self.assertEqual(self.tick().status, "retry")
        self.now += timedelta(seconds=30)
        self.assertEqual(self.tick().status, "idle")
        self.post.assert_called_once()
        self.now = self.now.replace(hour=13, minute=46)
        self.tick()
        self.assertEqual(PricemImportRun.objects.using("ideal").get().status, "missed")
        self.post.assert_called_once()

    def test_manual_retry_failed_snapshot_even_after_cutoff(self):
        with patch(
            "datapull_service.pricem.runner.persist_payload",
            side_effect=PayloadError("reconcile legacy duplicates"),
        ):
            result = self.tick()
        self.assertEqual(result.status, "failed")
        self.assertEqual(self.tick().status, "idle")
        self.now = self.now.replace(hour=13, minute=55)
        self.assertEqual(self.tick(retry_run_id=result.run_id).status, "succeeded")
        self.post.assert_called_once()

    def test_manual_retry_without_snapshot_cannot_bypass_cutoff(self):
        self.post.side_effect = requests.Timeout("network timeout")
        result = self.tick()
        self.now = self.now.replace(hour=13, minute=55)
        with self.assertRaises(ImportConfigurationError):
            self.tick(retry_run_id=result.run_id)
        self.post.assert_called_once()

    def test_invalid_payload_is_saved_but_does_not_write_partial_data(self):
        rows = export()
        rows[0]["sources"][0]["price"] = "invalid"
        self.post.return_value.text = json.dumps(rows)
        self.assertEqual(self.tick().status, "failed")
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 0)
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertTrue(PricemImportRun.objects.using("ideal").get().payload)

    def test_orphan_running_snapshot_is_recovered_without_api(self):
        raw = payload()
        PricemImportRun.objects.using("ideal").create(
            schedule=self.first,
            scheduled_at=self.now.replace(hour=9, minute=30),
            next_at=self.now.replace(hour=14, minute=15),
            status="running",
            attempts=1,
            payload=raw,
            payload_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
        self.assertEqual(self.tick().status, "succeeded")
        self.post.assert_not_called()

    def test_checksum_mismatch_prevents_import(self):
        run = PricemImportRun.objects.using("ideal").create(
            schedule=self.first,
            scheduled_at=self.now.replace(hour=9, minute=30),
            next_at=self.now.replace(hour=14, minute=15),
            status="running",
            attempts=1,
            payload=payload(),
            payload_hash="bad",
        )
        self.assertEqual(self.tick().status, "failed")
        run.refresh_from_db(using="ideal")
        self.assertIn("checksum", run.last_error)
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)

    def test_new_slot_updates_metadata_without_overriding_manual_mapping(self):
        self.assertEqual(self.tick().status, "succeeded")
        product = PRICEM_DATA_INT_Monitoring.objects.using("ideal").get()
        alternative = Tu.objects.using("ideal").create(
            xcode_tu="TU2", root_cu=self.tu.root_cu, status="ACT", type="A", cu_in_tu=5
        )
        product.root_tu = alternative
        product.save(using="ideal")
        rows = export()
        rows[0]["client_code"] = "new-code"
        rows[0]["sources"][0]["status"] = 2
        rows[0]["sources"][0]["formula"] = "new"
        self.post.return_value.text = json.dumps(rows)
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick().status, "succeeded")
        product.refresh_from_db(using="ideal")
        self.assertEqual(product.root_tu_id, alternative.pk)
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 1)
        self.assertEqual(
            PRICEM_DATA_Monitoring_Sources.objects.using("ideal").count(), 1
        )
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 2)

    def test_api_response_crossing_next_point_is_discarded(self):
        def response(*args, **kwargs):
            self.now = self.now.replace(hour=14, minute=16)
            return Mock(text=payload(), raise_for_status=Mock())

        self.post.side_effect = response
        self.assertEqual(self.tick().status, "missed")
        self.assertIsNone(PricemImportRun.objects.using("ideal").get().payload)
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)

    def test_success_log_failure_rolls_back_data_and_success_state(self):
        with patch(
            "datapull_service.pricem.runner.log_run",
            side_effect=[OperationalError("log write failed"), None],
        ):
            self.assertEqual(self.tick().status, "retry")
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertEqual(PricemImportRun.objects.using("ideal").get().status, "retry")

    def test_check_is_read_only(self):
        self.assertEqual(self.tick(check_only=True).status, "check")
        self.post.assert_not_called()
        self.assertEqual(PricemImportRun.objects.using("ideal").count(), 0)

    def test_failure_preserves_existing_prices_in_the_replaced_slot(self):
        slot = self.now.replace(hour=9, minute=30)
        products = normalize_payload(payload())
        products[0].sources[0].offers[0]["price"] = 55
        persist_payload(products, slot)

        def crash(items, scheduled_at):
            persist_payload(items, scheduled_at)
            raise OperationalError("failure after replacing the slot")

        with patch("datapull_service.pricem.runner.persist_payload", side_effect=crash):
            self.assertEqual(self.tick().status, "retry")
        self.assertEqual(
            PRICEM_DATA_Source_Offers.objects.using("ideal").get().price, 55
        )

    def test_legacy_rows_are_adopted_by_stable_fields(self):
        self.assertEqual(self.tick().status, "succeeded")
        product = PRICEM_DATA_INT_Monitoring.objects.using("ideal").get()
        source = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").get()
        product.priceva_product_id = None
        source.priceva_source_id = None
        product.save(using="ideal")
        source.save(using="ideal")
        rows = export()
        rows[0]["sources"][0]["status"] = 2
        self.post.return_value.text = json.dumps(rows)
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick().status, "succeeded")
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 1)
        self.assertEqual(
            PRICEM_DATA_Monitoring_Sources.objects.using("ideal").count(), 1
        )
        source.refresh_from_db(using="ideal")
        self.assertEqual(source.priceva_source_id, "opaque-source-1")
        self.assertEqual(source.status, 2)

    def test_ambiguous_legacy_mapping_fails_without_partial_writes(self):
        for _ in range(2):
            PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
                client_code="00001"
            )
        self.assertEqual(self.tick().status, "failed")
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 2)
        self.assertIn(
            "ambiguous existing rows",
            PricemImportRun.objects.using("ideal").get().last_error,
        )

    def test_unauthorized_api_response_is_not_retried_automatically(self):
        response = requests.Response()
        response.status_code = 401
        self.post.side_effect = requests.HTTPError("unauthorized", response=response)
        self.assertEqual(self.tick().status, "failed")
        self.now += timedelta(minutes=2)
        self.tick()
        self.post.assert_called_once()

    def test_attempt_limit_stops_automatic_retries(self):
        self.post.side_effect = requests.Timeout("temporary failure")
        for pause in (0, 61, 301, 901):
            self.now += timedelta(seconds=pause)
            self.tick()
        self.assertEqual(PricemImportRun.objects.using("ideal").get().status, "failed")
        self.now += timedelta(minutes=1)
        self.tick()
        self.assertEqual(self.post.call_count, 4)
