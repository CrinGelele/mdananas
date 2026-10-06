"""SQL persistence. The caller owns the transaction and the global import lock."""

from collections import defaultdict

from datapull_service.models.pricem_models import (
    PRICEM_DATA_EXT_Monitoring,
    PRICEM_DATA_INT_Monitoring,
    PRICEM_DATA_Monitoring_Additional_data,
    PRICEM_DATA_Monitoring_Sources,
    PRICEM_DATA_Source_Offers,
    PRICEM_LINK_Tags,
    PRICEM_REF_Tags,
)
from datapull_service.models.root_models import ROOT_PIVOT_Customer
from root_service.models.ref_sku_models import CMP, Cu, Mix, Tu

from .errors import PayloadError
from .schedule import MOSCOW


DB = "ideal"


def one(items, context):
    if len(items) > 1:
        ids = ", ".join(str(item.pk) for item in items[:10])
        raise PayloadError(
            f"{context}: ambiguous existing rows (IDs: {ids}); reconcile duplicates before retrying"
        )
    return items[0] if items else None


def index(items, key):
    result = defaultdict(list)
    for item in items:
        result[key(item)].append(item)
    return result


def update(obj, fields):
    changed = []
    for name, value in fields.items():
        if getattr(obj, name) != value:
            setattr(obj, name, value)
            changed.append(name)
    if changed:
        obj.save(using=DB, update_fields=changed)


class ImportStore:
    def __init__(self):
        products = list(PRICEM_DATA_INT_Monitoring.objects.using(DB).all()) + list(
            PRICEM_DATA_EXT_Monitoring.objects.using(DB).all()
        )
        self.products_by_id = index(products, lambda p: p.priceva_product_id)
        self.products_by_code = index(products, lambda p: p.client_code)
        sources = list(PRICEM_DATA_Monitoring_Sources.objects.using(DB).all())
        self.sources_by_id = index(sources, lambda s: s.priceva_source_id)
        self.sources_by_key = index(sources, self.source_key)
        self.customers = index(
            list(ROOT_PIVOT_Customer.objects.using(DB).all()),
            lambda c: (c.erp_name, c.shipped_to),
        )
        self.tags = index(
            list(PRICEM_REF_Tags.objects.using(DB).all()), lambda t: t.tag
        )
        self.links = set(
            PRICEM_LINK_Tags.objects.using(DB).values_list(
                "pricem_int_monitoring_id", "pricem_ext_monitoring_id", "pricem_tag_id"
            )
        )
        self.tus = index(list(Tu.objects.using(DB).all()), lambda p: p.xcode_tu)
        mixes = list(Mix.objects.using(DB).all())
        self.mixes = index(mixes, lambda p: p.xcode_mix)
        self.cmps = index(list(CMP.objects.using(DB).all()), lambda p: p.ean)
        self.brands = set(
            Cu.objects.using(DB).exclude(brand=None).values_list("brand", flat=True)
        )
        self.brands.update(p.brand for p in mixes if p.brand is not None)
        self.unmapped = 0

    @staticmethod
    def source_key(source):
        return (
            source.pricem_int_monitoring_id,
            source.pricem_ext_monitoring_id,
            source.url,
            source.root_pivot_customer_id,
            source.region,
            source.sale_option,
        )

    def product(self, item):
        obj = one(self.products_by_id[item.priceva_id], "Priceva product ID")
        if obj is None:
            legacy = [
                p
                for p in self.products_by_code[item.client_code]
                if p.priceva_product_id is None and p.client_code == item.client_code
            ]
            obj = one(legacy, "Legacy product client code")
        internal = (
            isinstance(obj, PRICEM_DATA_INT_Monitoring)
            if obj
            else item.fields["brand"] in self.brands
        )
        model = PRICEM_DATA_INT_Monitoring if internal else PRICEM_DATA_EXT_Monitoring
        fields = {
            "priceva_product_id": item.priceva_id,
            "client_code": item.client_code,
        }
        if not internal:
            fields.update(item.fields, material=item.article)
        if obj is None:
            obj = model.objects.using(DB).create(**fields)
        else:
            update(obj, fields)
        self.products_by_id[item.priceva_id] = [obj]
        # Preserve manual mappings. Automatic matching only fills unmapped entries.
        if internal and obj.root_tu_id is None and obj.root_mix_id is None:
            tus, mixes = (
                self.tus.get(item.article, []),
                self.mixes.get(item.article, []),
            )
            if len(tus) + len(mixes) == 1:
                update(
                    obj,
                    {
                        "root_tu_id": tus[0].pk if tus else None,
                        "root_mix_id": mixes[0].pk if mixes else None,
                        "is_mix": bool(mixes),
                    },
                )
        elif not internal and obj.root_cmp_id is None:
            cmps = self.cmps.get(item.article, [])
            if len(cmps) == 1:
                update(obj, {"root_cmp_id": cmps[0].pk})
        if (
            internal
            and obj.root_tu_id is None
            and obj.root_mix_id is None
            or not internal
            and obj.root_cmp_id is None
        ):
            self.unmapped += 1
        return obj, internal

    def customer(self, name):
        key = (name, name)
        customer = one(self.customers[key], "Customer name/shipped_to")
        if customer is None:
            customer = ROOT_PIVOT_Customer.objects.using(DB).create(
                erp_name=name, shipped_to=name
            )
            self.customers[key] = [customer]
        return customer

    def source(self, item, product, internal):
        customer = self.customer(item.company)
        fields = dict(
            item.fields,
            priceva_source_id=item.priceva_id,
            root_pivot_customer_id=customer.pk,
            pricem_int_monitoring_id=product.pk if internal else None,
            pricem_ext_monitoring_id=None if internal else product.pk,
        )
        obj = one(self.sources_by_id[item.priceva_id], "Priceva source ID")
        if obj is None:
            probe = PRICEM_DATA_Monitoring_Sources(**fields)
            legacy = [
                s
                for s in self.sources_by_key[self.source_key(probe)]
                if s.priceva_source_id is None
            ]
            obj = one(legacy, "Legacy monitoring source")
        if obj is None:
            obj = PRICEM_DATA_Monitoring_Sources.objects.using(DB).create(**fields)
        else:
            if (
                obj.pricem_int_monitoring_id != fields["pricem_int_monitoring_id"]
                or obj.pricem_ext_monitoring_id != fields["pricem_ext_monitoring_id"]
            ):
                raise PayloadError(
                    "Existing Priceva source belongs to another monitoring product"
                )
            update(obj, fields)
        self.sources_by_id[item.priceva_id] = [obj]
        return obj

    def add_tags(self, names, product, internal):
        for name in names:
            tag = one(self.tags[name], "Tag")
            if tag is None:
                tag = PRICEM_REF_Tags.objects.using(DB).create(tag=name)
                self.tags[name] = [tag]
            key = (
                product.pk if internal else None,
                None if internal else product.pk,
                tag.pk,
            )
            if key not in self.links:
                PRICEM_LINK_Tags.objects.using(DB).create(
                    pricem_int_monitoring_id=key[0],
                    pricem_ext_monitoring_id=key[1],
                    pricem_tag_id=key[2],
                )
                self.links.add(key)


def persist_payload(products, scheduled_at):
    store = ImportStore()
    slot = scheduled_at.astimezone(MOSCOW)
    offers, additional, source_ids = [], [], []
    for item in products:
        product, internal = store.product(item)
        store.add_tags(item.tags, product, internal)
        for source_item in item.sources:
            source = store.source(source_item, product, internal)
            source_ids.append(source.pk)
            offers.extend(
                PRICEM_DATA_Source_Offers(
                    pricem_source_id=source.pk,
                    upload_date=slot.date(),
                    upload_time=slot.time().replace(tzinfo=None),
                    **offer,
                )
                for offer in source_item.offers
            )
            additional.extend(
                PRICEM_DATA_Monitoring_Additional_data(
                    pricem_source_id=source.pk, **fields
                )
                for fields in source_item.additional
            )
    # A saved export is authoritative for its slot. This also reconciles partial
    # legacy imports with the same slot without touching other dates or times.
    PRICEM_DATA_Source_Offers.objects.using(DB).filter(
        upload_date=slot.date(), upload_time=slot.time().replace(tzinfo=None)
    ).delete()
    PRICEM_DATA_Source_Offers.objects.using(DB).bulk_create(offers, batch_size=100)
    for start in range(0, len(source_ids), 200):
        PRICEM_DATA_Monitoring_Additional_data.objects.using(DB).filter(
            pricem_source_id__in=source_ids[start : start + 200]
        ).delete()
    PRICEM_DATA_Monitoring_Additional_data.objects.using(DB).bulk_create(
        additional, batch_size=100
    )
    return {
        "products": len(products),
        "sources": len(source_ids),
        "offers": len(offers),
        "additional": len(additional),
        "unmapped_products": store.unmapped,
    }
