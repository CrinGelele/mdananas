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
    PRICEM_DATA_EXT_Monitoring,
    PRICEM_DATA_Monitoring_Additional_data,
    PRICEM_DATA_Monitoring_Sources,
    PRICEM_DATA_Source_Offers,
)
from datapull_service.pricem.errors import ImportConfigurationError, PayloadError
from datapull_service.pricem.runner import run_tick
from datapull_service.pricem.schedule import MOSCOW
from datapull_service.pricem.store import persist_payload
from datapull_service.pricem.payload import normalize_payload
from root_service.models.ref_sku_models import CMP, Cu, Tu


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

    def legacy_source_duplicates(self):
        historical_slot = (self.now - timedelta(days=1)).replace(hour=9, minute=30)
        persist_payload(normalize_payload(payload()), historical_slot)
        product = PRICEM_DATA_INT_Monitoring.objects.using("ideal").get()
        product.priceva_product_id = None
        product.save(using="ideal")
        source = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").get()
        source.priceva_source_id = None
        source.save(using="ideal")
        source_ids = [source.pk]
        for status in (2, 3):
            duplicate = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").create(
                pricem_int_monitoring=product,
                url=source.url,
                root_pivot_customer_id=source.root_pivot_customer_id,
                region=source.region,
                sale_option=source.sale_option,
                status=status,
                formula=f"old-{status}",
            )
            source_ids.append(duplicate.pk)
            PRICEM_DATA_Source_Offers.objects.using("ideal").create(
                pricem_source=duplicate,
                upload_date=historical_slot.date(),
                upload_time=time(9, 30),
                offer="old offer",
                price=status * 10,
            )
            PRICEM_DATA_Monitoring_Additional_data.objects.using("ideal").create(
                pricem_source=duplicate, header="legacy", value=str(status)
            )
        return product, source_ids

    def legacy_source_data(self, source_ids):
        return {
            "sources": list(
                PRICEM_DATA_Monitoring_Sources.objects.using("ideal")
                .filter(pk__in=source_ids)
                .order_by("id")
                .values()
            ),
            "offers": list(
                PRICEM_DATA_Source_Offers.objects.using("ideal")
                .filter(pricem_source_id__in=source_ids)
                .order_by("id")
                .values()
            ),
            "additional": list(
                PRICEM_DATA_Monitoring_Additional_data.objects.using("ideal")
                .filter(pricem_source_id__in=source_ids)
                .order_by("id")
                .values()
            ),
        }

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
        for code in ("MANUAL1", "MANUAL2"):
            manual = Tu.objects.using("ideal").create(
                xcode_tu=code,
                root_cu=self.tu.root_cu,
                status="ACT",
                type="A",
                cu_in_tu=5,
            )
            PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
                client_code="00001", root_tu=manual
            )
        self.assertEqual(self.tick().status, "failed")
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 2)
        self.assertIn(
            "conflicting product kinds or manual mappings",
            PricemImportRun.objects.using("ideal").get().last_error,
        )

    def test_unmapped_legacy_product_duplicates_get_a_new_stable_id(self):
        legacy = [
            PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
                client_code="00001"
            )
            for _ in range(2)
        ]
        self.assertEqual(self.tick().status, "succeeded")
        current = PRICEM_DATA_INT_Monitoring.objects.using("ideal").get(
            priceva_product_id="opaque-product-1"
        )
        self.assertNotIn(current.pk, [product.pk for product in legacy])
        self.assertEqual(current.root_tu_id, self.tu.pk)
        for product in legacy:
            product.refresh_from_db(using="ideal")
            self.assertIsNone(product.priceva_product_id)
            self.assertIsNone(product.root_tu_id)
        run = PricemImportRun.objects.using("ideal").get()
        self.assertEqual(
            json.loads(run.counts)["products_created_for_legacy_duplicates"], 1
        )
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick().status, "succeeded")
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 3)

    def test_common_manual_mapping_is_copied_even_if_it_differs_from_article(self):
        manual = Tu.objects.using("ideal").create(
            xcode_tu="MANUAL",
            root_cu=self.tu.root_cu,
            status="ACT",
            type="A",
            cu_in_tu=5,
        )
        legacy = [
            PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
                client_code="00001", root_tu=manual, is_mix=False
            )
            for _ in range(2)
        ]
        self.assertEqual(self.tick().status, "succeeded")
        current = PRICEM_DATA_INT_Monitoring.objects.using("ideal").get(
            priceva_product_id="opaque-product-1"
        )
        self.assertNotIn(current.pk, [product.pk for product in legacy])
        self.assertEqual(current.root_tu_id, manual.pk)
        self.assertIs(current.is_mix, False)

    def test_article_selects_unique_existing_internal_mapping(self):
        manual = Tu.objects.using("ideal").create(
            xcode_tu="OLD", root_cu=self.tu.root_cu, status="ACT", type="A", cu_in_tu=5
        )
        old = PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
            client_code="00001", root_tu=manual, is_mix=False
        )
        current = PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
            client_code="00001", root_tu=self.tu, is_mix=False
        )
        self.assertEqual(self.tick().status, "succeeded")
        current.refresh_from_db(using="ideal")
        old.refresh_from_db(using="ideal")
        self.assertEqual(current.priceva_product_id, "opaque-product-1")
        self.assertEqual(current.root_tu_id, self.tu.pk)
        self.assertIsNone(old.priceva_product_id)
        self.assertEqual(old.root_tu_id, manual.pk)
        self.assertEqual(PRICEM_DATA_INT_Monitoring.objects.using("ideal").count(), 2)

    def test_saved_external_duplicate_uses_article_ean_rather_than_client_code(self):
        old_cmp = CMP.objects.using("ideal").create(ean="4006303001641")
        current_cmp = CMP.objects.using("ideal").create(ean="4006303005625")
        old = PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
            client_code="4006303001641", root_cmp=old_cmp, material=old_cmp.ean
        )
        current = PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
            client_code="4006303001641", root_cmp=current_cmp, material=current_cmp.ean
        )
        source = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").create(
            pricem_ext_monitoring=old, url="https://shop.invalid/old"
        )
        historical_offer = PRICEM_DATA_Source_Offers.objects.using("ideal").create(
            pricem_source=source,
            upload_date=self.now.date() - timedelta(days=1),
            upload_time=time(9, 30),
            offer="",
            price=55,
        )
        rows = export(brand="FLEUR ALPINE")
        rows[0].update(id="cx", client_code=old.client_code, article=current_cmp.ean)
        raw = json.dumps(rows)
        run = PricemImportRun.objects.using("ideal").create(
            schedule=self.first,
            scheduled_at=self.now.replace(hour=9, minute=30),
            next_at=self.now.replace(hour=14, minute=15),
            status="failed",
            attempts=2,
            payload=raw,
            payload_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick(retry_run_id=run.pk).status, "succeeded")
        self.post.assert_not_called()
        old.refresh_from_db(using="ideal")
        current.refresh_from_db(using="ideal")
        source.refresh_from_db(using="ideal")
        historical_offer.refresh_from_db(using="ideal")
        self.assertIsNone(old.priceva_product_id)
        self.assertEqual(old.root_cmp_id, old_cmp.pk)
        self.assertEqual(current.priceva_product_id, "cx")
        self.assertEqual(current.root_cmp_id, current_cmp.pk)
        self.assertEqual(source.pricem_ext_monitoring_id, old.pk)
        self.assertEqual(historical_offer.price, 55)
        self.assertEqual(PRICEM_DATA_EXT_Monitoring.objects.using("ideal").count(), 2)
        new_source = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").get(
            priceva_source_id="opaque-source-1"
        )
        self.assertEqual(new_source.pricem_ext_monitoring_id, current.pk)

    def test_multiple_article_matches_still_require_an_explicit_choice(self):
        for _ in range(2):
            cmp = CMP.objects.using("ideal").create(ean="TU1")
            PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
                client_code="00001", root_cmp=cmp
            )
        self.assertEqual(self.tick().status, "failed")
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)
        self.assertEqual(PRICEM_DATA_EXT_Monitoring.objects.using("ideal").count(), 2)

    def test_product_preflight_reports_multiple_conflicts_before_any_product_write(
        self,
    ):
        rows = export()
        rows.append(export()[0])
        rows[1].update(id="other-product", client_code="00002")
        rows[1]["sources"][0]["id"] = "other-source"
        self.post.return_value.text = json.dumps(rows)
        for code in ("00001", "00002"):
            for ean in ("OTHER1", "OTHER2"):
                cmp = CMP.objects.using("ideal").create(ean=ean)
                PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
                    client_code=code, root_cmp=cmp
                )
        with patch("datapull_service.pricem.store.ImportStore.product") as write:
            self.assertEqual(self.tick().status, "failed")
        write.assert_not_called()
        run = PricemImportRun.objects.using("ideal").get()
        self.assertIn("2 conflict(s)", run.last_error)
        self.assertIn("00001", run.last_error)
        self.assertIn("00002", run.last_error)
        self.assertIn("EXT:", run.last_error)
        self.assertEqual(PRICEM_DATA_Source_Offers.objects.using("ideal").count(), 0)

    def test_legacy_source_duplicates_get_new_id_without_changing_history(self):
        product, source_ids = self.legacy_source_duplicates()
        manual_tu = Tu.objects.using("ideal").create(
            xcode_tu="MANUAL",
            root_cu=self.tu.root_cu,
            status="ACT",
            type="A",
            cu_in_tu=5,
        )
        product.root_tu = manual_tu
        product.save(using="ideal")
        historical = self.legacy_source_data(source_ids)

        self.assertEqual(self.tick().status, "succeeded")
        source = PRICEM_DATA_Monitoring_Sources.objects.using("ideal").get(
            priceva_source_id="opaque-source-1"
        )
        self.assertNotIn(source.pk, source_ids)
        self.assertEqual(source.pricem_int_monitoring_id, product.pk)
        product.refresh_from_db(using="ideal")
        self.assertEqual(product.root_tu_id, manual_tu.pk)
        self.assertEqual(self.legacy_source_data(source_ids), historical)
        current_offer = PRICEM_DATA_Source_Offers.objects.using("ideal").get(
            upload_date=self.now.date(), upload_time=time(9, 30)
        )
        self.assertEqual(current_offer.pricem_source_id, source.pk)
        counts = json.loads(PricemImportRun.objects.using("ideal").get().counts)
        self.assertEqual(counts["sources_created_for_legacy_duplicates"], 1)

        self.assertEqual(self.tick().status, "idle")
        rows = export()
        rows[0]["sources"][0].update(status=2, formula="new")
        self.post.return_value.text = json.dumps(rows)
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick().status, "succeeded")
        source.refresh_from_db(using="ideal")
        self.assertEqual(source.status, 2)
        self.assertEqual(source.formula, "new")
        self.assertEqual(
            PRICEM_DATA_Monitoring_Sources.objects.using("ideal").count(), 4
        )
        self.assertEqual(self.legacy_source_data(source_ids), historical)
        latest = PricemImportRun.objects.using("ideal").latest("scheduled_at")
        self.assertEqual(
            json.loads(latest.counts)["sources_created_for_legacy_duplicates"], 0
        )

    def test_failed_snapshot_with_legacy_source_duplicates_can_retry_after_replacement(
        self,
    ):
        _, source_ids = self.legacy_source_duplicates()
        historical = self.legacy_source_data(source_ids)
        raw = payload()
        run = PricemImportRun.objects.using("ideal").create(
            schedule=self.first,
            scheduled_at=self.now.replace(hour=9, minute=30),
            next_at=self.now.replace(hour=14, minute=15),
            status="failed",
            attempts=1,
            payload=raw,
            payload_hash=hashlib.sha256(raw.encode()).hexdigest(),
            last_error="Legacy monitoring source: ambiguous existing rows",
        )
        self.now = self.now.replace(hour=14, minute=16)
        self.assertEqual(self.tick(retry_run_id=run.pk).status, "succeeded")
        self.post.assert_not_called()
        run.refresh_from_db(using="ideal")
        self.assertEqual(run.attempts, 2)
        self.assertEqual(self.legacy_source_data(source_ids), historical)
        offer = PRICEM_DATA_Source_Offers.objects.using("ideal").get(
            upload_date=self.now.date(), upload_time=time(9, 30)
        )
        self.assertNotIn(offer.pricem_source_id, source_ids)

    def test_new_source_for_legacy_duplicates_rolls_back_and_recovers(self):
        product, source_ids = self.legacy_source_duplicates()
        historical = self.legacy_source_data(source_ids)

        def crash(products, scheduled_at):
            persist_payload(products, scheduled_at)
            raise OperationalError(
                "failure after creating a source for legacy duplicates"
            )

        with patch("datapull_service.pricem.runner.persist_payload", side_effect=crash):
            self.assertEqual(self.tick().status, "retry")
        self.assertEqual(
            PRICEM_DATA_Monitoring_Sources.objects.using("ideal").count(), 3
        )
        self.assertEqual(self.legacy_source_data(source_ids), historical)
        product.refresh_from_db(using="ideal")
        self.assertIsNone(product.priceva_product_id)
        self.now += timedelta(seconds=61)
        self.assertEqual(self.tick().status, "succeeded")
        self.post.assert_called_once()
        self.assertEqual(
            PRICEM_DATA_Monitoring_Sources.objects.using("ideal").count(), 4
        )
        self.assertEqual(self.legacy_source_data(source_ids), historical)

    def test_explicit_priceva_source_id_conflict_still_fails(self):
        _, source_ids = self.legacy_source_duplicates()
        other = PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
            client_code="other"
        )
        PRICEM_DATA_Monitoring_Sources.objects.using("ideal").filter(
            pk=source_ids[0]
        ).update(priceva_source_id="opaque-source-1", pricem_int_monitoring=other)
        historical = self.legacy_source_data(source_ids)
        self.assertEqual(self.tick().status, "failed")
        self.assertEqual(self.legacy_source_data(source_ids), historical)
        run = PricemImportRun.objects.using("ideal").get()
        self.assertIn("belongs to another monitoring product", run.last_error)

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
