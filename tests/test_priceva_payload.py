import json
from pathlib import Path
import unittest

import tests  # noqa: F401 -- adds the Django project directory to sys.path
from datapull_service.pricem.errors import PayloadError, safe_error
from datapull_service.pricem.payload import normalize_payload
from tests.support import export, payload


class PayloadTests(unittest.TestCase):
    def test_full_repository_fixture(self):
        path = (
            Path(__file__).resolve().parent.parent
            / "mdananas/datapull_service/views/data.json"
        )
        products = normalize_payload(path.read_text())
        self.assertEqual(len(products), 510)
        self.assertEqual(sum(len(p.sources) for p in products), 5488)
        self.assertEqual(sum(len(s.offers) for p in products for s in p.sources), 5797)

    def test_single_source_without_vendor_label_or_date(self):
        rows = export()
        rows[0]["sources"][0]["last_check_date"] = ""
        offer = normalize_payload(json.dumps(rows))[0].sources[0].offers[0]
        self.assertEqual(offer["offer"], "")
        self.assertIsNone(offer["last_check_date"])

    def test_nested_offers_and_leading_zero_codes(self):
        product = normalize_payload(payload(nested=True))[0]
        self.assertEqual(product.client_code, "00001")
        self.assertEqual(len(product.sources[0].offers), 2)
        self.assertEqual(product.priceva_id, "opaque-product-1")

    def test_bad_values_are_rejected_with_record_path(self):
        for field, value in [
            ("price", "not-a-number"),
            ("status", 40000),
            ("last_check_date", "not-a-date"),
            ("formula", "x" * 11),
            ("in_stock", "yes"),
            ("relevance_status", 40000),
        ]:
            with self.subTest(field=field):
                rows = export()
                rows[0]["sources"][0][field] = value
                with self.assertRaisesRegex(
                    PayloadError, r"products\[0\].sources\[0\]"
                ):
                    normalize_payload(json.dumps(rows))

    def test_duplicate_ids_and_empty_export(self):
        rows = export()
        rows.append(rows[0])
        for data in ("[]", "{}", "not-json", json.dumps(rows)):
            with self.assertRaises(PayloadError):
                normalize_payload(data)

    def test_errors_do_not_expose_export_query_or_credentials(self):
        result = safe_error(
            ValueError(
                "POST https://user:pass@host.invalid/export?f=private-secret password=secret"
            )
        )
        self.assertNotIn("private-secret", result)
        self.assertNotIn("user:pass", result)
        self.assertNotIn("password=secret", result)
