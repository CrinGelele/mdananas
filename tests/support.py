import json
import os
import unittest

os.environ["DJANGO_SETTINGS_MODULE"] = "tests.settings"
import django

django.setup()

from django.apps import apps
from django.db import connections


MODELS = list(apps.get_models())
for model in MODELS:
    model._meta.db_table = f"{model._meta.app_label}_{model._meta.model_name}"
with connections["ideal"].schema_editor() as editor:
    for model in MODELS:
        editor.create_model(model)


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        with connections["ideal"].cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys = OFF")
            for model in MODELS:
                cursor.execute(f'DELETE FROM "{model._meta.db_table}"')
            cursor.execute("PRAGMA foreign_keys = ON")


def export(brand="OWN", nested=False):
    source = {
        "id": "opaque-source-1",
        "url": "https://shop.invalid/item",
        "company_name": "Shop",
        "region_name": "Moscow",
        "status": 1,
        "option": "",
        "formula": "",
        "last_check_date": 1700000000,
        "currency": "RUB",
        "in_stock": 1,
        "price": 100,
        "discount": 0,
        "original_price": None,
        "original_currency": None,
        "relevance_status": 1,
        "offers": None,
        "data": [{"header": "size", "value": "10"}],
    }
    if nested:
        source["offers"] = [
            {**source, "offer": "Vendor A"},
            {**source, "offer": "Vendor B", "price": 105},
        ]
    return [
        {
            "id": "opaque-product-1",
            "client_code": "00001",
            "article": "TU1",
            "brand_name": brand,
            "category_name": "Food",
            "name": "Product",
            "tags": ["tag"],
            "sources": [source],
        }
    ]


def payload(**kwargs):
    return json.dumps(export(**kwargs))
