from contextlib import nullcontext
from datetime import datetime
import hashlib
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db import OperationalError

from tests.support import DatabaseTest, payload
from datapull_service.models.pricem_models import (
    PricemImportRun,
    TaskSchedule,
    PRICEM_DATA_EXT_Monitoring,
    PRICEM_DATA_INT_Monitoring,
)
from datapull_service.pricem.bindings import bind_product
from datapull_service.pricem.errors import ImportConfigurationError, PayloadError
from datapull_service.pricem.schedule import MOSCOW
from datapull_service.pricem.payload import normalize_payload
from datapull_service.pricem.store import persist_payload
from root_service.models.ref_sku_models import CMP


class BindingTests(DatabaseTest):
    def setUp(self):
        super().setUp()
        slot = datetime(2026, 10, 6, 9, 30, tzinfo=MOSCOW)
        schedule = TaskSchedule.objects.using("ideal").create(
            time_hour=9, time_minute=30
        )
        raw = payload()
        self.run = PricemImportRun.objects.using("ideal").create(
            schedule=schedule,
            scheduled_at=slot,
            next_at=slot.replace(hour=14),
            status="failed",
            attempts=2,
            payload=raw,
            payload_hash=hashlib.sha256(raw.encode()).hexdigest(),
        )
        self.target = PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
            client_code="00001", root_cmp=CMP.objects.using("ideal").create(ean="TU1")
        )
        self.other = PRICEM_DATA_EXT_Monitoring.objects.using("ideal").create(
            client_code="00001", root_cmp=CMP.objects.using("ideal").create(ean="OLD")
        )
        lock = patch(
            "datapull_service.pricem.bindings.import_lock",
            return_value=nullcontext(True),
        )
        self.lock = lock.start()
        self.addCleanup(lock.stop)
        assertion = patch("datapull_service.pricem.bindings.assert_import_lock")
        assertion.start()
        self.addCleanup(assertion.stop)

    def bind(self, **kwargs):
        return bind_product(self.run.pk, "00001", "ext", self.target.pk, **kwargs)

    def test_preview_does_not_change_products_or_run(self):
        before = list(
            PRICEM_DATA_EXT_Monitoring.objects.using("ideal").order_by("id").values()
        )
        plan = self.bind(check_only=True)
        self.assertEqual(plan.priceva_id, "opaque-product-1")
        self.assertEqual(plan.mapping, {"root_cmp_id": self.target.root_cmp_id})
        self.assertEqual(
            list(
                PRICEM_DATA_EXT_Monitoring.objects.using("ideal")
                .order_by("id")
                .values()
            ),
            before,
        )
        self.lock.assert_not_called()
        self.run.refresh_from_db(using="ideal")
        self.assertEqual(self.run.status, "failed")
        self.assertEqual(self.run.attempts, 2)

    def test_binding_changes_only_priceva_id_and_is_idempotent(self):
        before = (
            PRICEM_DATA_EXT_Monitoring.objects.using("ideal")
            .filter(pk=self.target.pk)
            .values()
            .get()
        )
        self.assertTrue(self.bind().changed)
        before["priceva_product_id"] = "opaque-product-1"
        self.assertEqual(
            PRICEM_DATA_EXT_Monitoring.objects.using("ideal")
            .filter(pk=self.target.pk)
            .values()
            .get(),
            before,
        )
        self.other.refresh_from_db(using="ideal")
        self.assertIsNone(self.other.priceva_product_id)
        self.assertFalse(self.bind().changed)
        self.run.refresh_from_db(using="ideal")
        self.assertEqual(self.run.status, "failed")
        self.assertEqual(self.run.attempts, 2)

    def test_explicit_binding_keeps_manual_mapping_during_import(self):
        self.target.root_cmp = self.other.root_cmp
        self.target.save(using="ideal")
        self.bind()
        persist_payload(normalize_payload(self.run.payload), self.run.scheduled_at)
        self.target.refresh_from_db(using="ideal")
        self.assertEqual(self.target.root_cmp_id, self.other.root_cmp_id)
        self.assertEqual(self.target.priceva_product_id, "opaque-product-1")

    def test_write_failure_rolls_back_binding(self):
        original = PRICEM_DATA_EXT_Monitoring.save

        def crash(instance, *args, **kwargs):
            original(instance, *args, **kwargs)
            raise OperationalError("failure after saving binding")

        with patch.object(PRICEM_DATA_EXT_Monitoring, "save", new=crash):
            with self.assertRaises(OperationalError):
                self.bind()
        self.target.refresh_from_db(using="ideal")
        self.assertIsNone(self.target.priceva_product_id)

    def test_cannot_bind_id_already_owned_by_another_product_or_kind(self):
        PRICEM_DATA_INT_Monitoring.objects.using("ideal").create(
            client_code="00001", priceva_product_id="opaque-product-1"
        )
        with self.assertRaisesRegex(ImportConfigurationError, "already bound to INT"):
            self.bind()
        self.target.refresh_from_db(using="ideal")
        self.assertIsNone(self.target.priceva_product_id)

    def test_cannot_replace_another_priceva_id(self):
        self.target.priceva_product_id = "another-id"
        self.target.save(using="ideal")
        with self.assertRaisesRegex(ImportConfigurationError, "another Priceva ID"):
            self.bind()

    def test_selected_row_must_have_the_saved_client_code(self):
        self.target.client_code = "different"
        self.target.save(using="ideal")
        with self.assertRaisesRegex(ImportConfigurationError, "another client code"):
            self.bind()

    def test_checksum_and_snapshot_are_required(self):
        self.run.payload_hash = "invalid"
        self.run.save(using="ideal")
        with self.assertRaisesRegex(PayloadError, "checksum"):
            self.bind()
        self.run.payload = None
        self.run.save(using="ideal")
        with self.assertRaisesRegex(PayloadError, "no saved snapshot"):
            self.bind()

    def test_busy_importer_prevents_binding(self):
        self.lock.return_value = nullcontext(False)
        with self.assertRaisesRegex(ImportConfigurationError, "Another process"):
            self.bind()
        self.target.refresh_from_db(using="ideal")
        self.assertIsNone(self.target.priceva_product_id)

    def test_command_preview_reports_selected_mapping(self):
        output = StringIO()
        with patch(
            "datapull_service.management.commands.pricem_bind_product.verify_schema"
        ):
            call_command(
                "pricem_bind_product",
                run=self.run.pk,
                client_code="00001",
                kind="ext",
                product_id=self.target.pk,
                check=True,
                stdout=output,
            )
        self.assertIn("check:", output.getvalue())
        self.assertIn(f"target=EXT:{self.target.pk}", output.getvalue())
        self.target.refresh_from_db(using="ideal")
        self.assertIsNone(self.target.priceva_product_id)
