"""Explicitly bind a saved Priceva product to a user-selected monitoring row."""

from dataclasses import dataclass
import hashlib

from django.db import transaction

from datapull_service.models.pricem_models import (
    PricemImportRun,
    PRICEM_DATA_EXT_Monitoring,
    PRICEM_DATA_INT_Monitoring,
)

from .errors import ImportConfigurationError, PayloadError
from .locking import assert_import_lock, import_lock
from .payload import normalize_payload
from .store import DB, ImportStore


MODELS = {"int": PRICEM_DATA_INT_Monitoring, "ext": PRICEM_DATA_EXT_Monitoring}


@dataclass(frozen=True)
class ProductBinding:
    run_id: int
    client_code: str
    priceva_id: str
    kind: str
    product_id: int
    mapping: dict
    changed: bool = False


def binding_plan(run_id, client_code, kind, product_id):
    run = PricemImportRun.objects.using(DB).get(pk=run_id)
    if run.status == "succeeded":
        raise ImportConfigurationError(
            "The run already succeeded; binding is not needed"
        )
    if not run.payload:
        raise PayloadError("The run has no saved snapshot")
    if hashlib.sha256(run.payload.encode("utf-8")).hexdigest() != run.payload_hash:
        raise PayloadError("Saved snapshot checksum does not match")
    items = [
        item
        for item in normalize_payload(run.payload)
        if item.client_code == client_code
    ]
    if len(items) != 1:
        raise ImportConfigurationError(
            "Client code was not found in the saved snapshot"
        )
    item = items[0]
    model = MODELS[kind]
    target = model.objects.using(DB).get(pk=product_id)
    if target.client_code != item.client_code:
        raise ImportConfigurationError(
            "Selected monitoring row has another client code"
        )
    if target.priceva_product_id not in (None, item.priceva_id):
        raise ImportConfigurationError("Selected monitoring row has another Priceva ID")
    for other_kind, other_model in MODELS.items():
        for other in other_model.objects.using(DB).filter(
            priceva_product_id=item.priceva_id
        ):
            if other_kind != kind or other.pk != target.pk:
                raise ImportConfigurationError(
                    f"Priceva ID is already bound to {other_kind.upper()}:{other.pk}"
                )
    return target, ProductBinding(
        run.pk,
        item.client_code,
        item.priceva_id,
        kind.upper(),
        target.pk,
        ImportStore.product_mapping(target),
        changed=target.priceva_product_id is None,
    )


def bind_product(run_id, client_code, kind, product_id, check_only=False):
    if check_only:
        return binding_plan(run_id, client_code, kind, product_id)[1]
    with import_lock() as acquired:
        if not acquired:
            raise ImportConfigurationError("Another process is importing Priceva")
        assert_import_lock()
        with transaction.atomic(using=DB):
            target, plan = binding_plan(run_id, client_code, kind, product_id)
            assert_import_lock()
            if plan.changed:
                target.priceva_product_id = plan.priceva_id
                target.save(using=DB, update_fields=["priceva_product_id"])
        return plan
