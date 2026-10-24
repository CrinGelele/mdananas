from django.db import models
from root_service.models.ref_sku_models import Cu, CMP


class BY_TMP_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    store_by = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    material_desc = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    purchase_price_value = models.CharField(max_length=255)
    fact_price_value = models.CharField(max_length=255)

    class Meta:
       managed = False
       db_table = '[15_BY].[BY_STAGE_Sales_Draft]'


class BY_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True)
    root_cmp = models.ForeignKey(CMP, on_delete=models.PROTECT, null=True, blank=True)
    material = models.TextField()
    by_description = models.TextField()
    by_competitor_sku = models.ForeignKey('BY_REF_Competitor_SKU', on_delete=models.PROTECT, null=True)
    is_last_upload = models.BooleanField()

    class Meta:
       managed = False
       db_table = '[15_BY].[BY_PIVOT_SKU]'


class BY_REF_Store(models.Model):
    store_by = models.TextField()
    chain_name = models.CharField(max_length=55, null=True, blank=True)
    channel = models.CharField(max_length=30, null=True, blank=True)
    address_city = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
       managed = False
       db_table = '[15_BY].[BY_REF_Stores]'


class BY_REF_Competitor_SKU(models.Model):
    brand = models.CharField(max_length=15, null=True, blank=True)
    category = models.CharField(max_length=15, null=True, blank=True)
    groupname = models.CharField(max_length=25, null=True, blank=True)

    class Meta:
       managed = False
       db_table = '[15_BY].[BY_REF_Competitors_SKU]'
