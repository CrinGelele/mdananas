"""Validate an entire export before making changes to SQL Server."""

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from .errors import PayloadError


def fail(path, message):
    # Paths identify a record without putting its contents into logs.
    raise PayloadError(f"{path}: {message}")


def text(value, path, limit=None, required=False, empty=None):
    if value is None or value == "":
        if required:
            fail(path, "required value is empty")
        return empty
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        fail(path, "expected a string or number")
    if isinstance(value, float) and not math.isfinite(value):
        fail(path, "non-finite numeric text")
    result = (
        str(int(value))
        if isinstance(value, float) and value.is_integer()
        else str(value)
    )
    if limit and len(result) > limit:
        fail(path, f"value exceeds {limit} characters")
    return result


def integer(value, path, required=False):
    if value is None or value == "":
        if required:
            fail(path, "required integer is empty")
        return None
    try:
        result = int(value)
        if isinstance(value, bool) or Decimal(str(value)) != result:
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError, InvalidOperation):
        fail(path, "invalid integer")


def external_id(value, path):
    # Priceva IDs are opaque strings, not necessarily decimal numbers.
    return text(value, path, 100, required=True)


def number(value, path):
    if value is None or value == "":
        return None
    try:
        result = float(value)
        if isinstance(value, bool) or not math.isfinite(result):
            raise ValueError
        return result
    except (TypeError, ValueError, OverflowError):
        fail(path, "invalid finite number")


def boolean(value, path):
    if value is None or value == "":
        return None
    if value in (0, 1, False, True):
        return bool(value)
    fail(path, "expected 0, 1 or null")


def timestamp(value, path):
    value = integer(value, path)
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        fail(path, "timestamp outside supported range")


def objects(value, path):
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        fail(path, "expected a list of objects")
    return value


@dataclass
class Source:
    priceva_id: str
    company: str
    fields: dict
    offers: list
    additional: list


@dataclass
class Product:
    priceva_id: str
    client_code: str
    article: str | None
    fields: dict
    tags: list
    sources: list


def normalize_offer(row, path):
    relevance = integer(row.get("relevance_status"), path + ".relevance_status")
    if relevance is not None and not -32768 <= relevance <= 32767:
        fail(path + ".relevance_status", "value exceeds SQL smallint")
    return {
        "currency": text(row.get("currency"), path + ".currency", 3),
        "last_check_date": timestamp(
            row.get("last_check_date"), path + ".last_check_date"
        ),
        "relevance_status": relevance,
        "in_stock": boolean(row.get("in_stock"), path + ".in_stock"),
        "price": number(row.get("price"), path + ".price"),
        "discount": number(row.get("discount"), path + ".discount"),
        "original_currency": text(
            row.get("original_currency"), path + ".original_currency", 3
        ),
        "original_price": number(row.get("original_price"), path + ".original_price"),
        # A source with a single offer has no vendor label in Priceva's export.
        "offer": text(row.get("offer"), path + ".offer", empty=""),
    }


def normalize_payload(payload):
    try:
        rows = json.loads(payload)
    except (ValueError, TypeError) as error:
        raise PayloadError("Export is not valid JSON") from error
    if not isinstance(rows, list) or not rows:
        fail("export", "expected a non-empty list of products")
    result, product_ids, source_ids, codes = [], set(), set(), set()
    for index, row in enumerate(rows):
        path = f"products[{index}]"
        if not isinstance(row, dict):
            fail(path, "expected an object")
        pid = external_id(row.get("id"), path + ".id")
        code = text(row.get("client_code"), path + ".client_code", 30, required=True)
        if pid in product_ids or code in codes:
            fail(path, "duplicate product ID or client code")
        product_ids.add(pid)
        codes.add(code)
        tags = row.get("tags") or []
        if not isinstance(tags, list):
            fail(path + ".tags", "expected a list")
        tags = list(
            dict.fromkeys(text(tag, path + ".tags", required=True) for tag in tags)
        )
        sources = []
        for source_index, source in enumerate(
            objects(row.get("sources"), path + ".sources")
        ):
            spath = f"{path}.sources[{source_index}]"
            sid = external_id(source.get("id"), spath + ".id")
            if sid in source_ids:
                fail(spath, "duplicate source ID")
            source_ids.add(sid)
            offer_rows = (
                [source]
                if source.get("offers") is None
                else objects(source["offers"], spath + ".offers")
            )
            offers = [
                normalize_offer(offer, f"{spath}.offers[{i}]")
                for i, offer in enumerate(offer_rows)
            ]
            if len({offer["offer"] for offer in offers}) != len(offers):
                fail(spath + ".offers", "duplicate vendor labels within a source")
            additional = []
            for item in objects(source.get("data"), spath + ".data"):
                additional.append(
                    {
                        "header": text(item.get("header"), spath + ".data.header"),
                        "value": text(item.get("value"), spath + ".data.value"),
                    }
                )
            status = integer(source.get("status"), spath + ".status")
            if status is not None and not -32768 <= status <= 32767:
                fail(spath + ".status", "value exceeds SQL smallint")
            sources.append(
                Source(
                    sid,
                    text(
                        source.get("company_name"),
                        spath + ".company_name",
                        required=True,
                    ),
                    {
                        "url": text(source.get("url"), spath + ".url", required=True),
                        "region": text(
                            source.get("region_name"), spath + ".region_name", 30
                        ),
                        "status": status,
                        "sale_option": text(
                            source.get("option"), spath + ".option", 10
                        ),
                        "formula": text(source.get("formula"), spath + ".formula", 10),
                    },
                    offers,
                    additional,
                )
            )
        result.append(
            Product(
                pid,
                code,
                text(row.get("article"), path + ".article", 30),
                {
                    "pricem_description": text(row.get("name"), path + ".name"),
                    "category": text(
                        row.get("category_name"), path + ".category_name", 30
                    ),
                    "brand": text(row.get("brand_name"), path + ".brand_name", 30),
                },
                tags,
                sources,
            )
        )
    return result
