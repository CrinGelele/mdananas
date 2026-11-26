from django.db import models
from root_service.models.ref_sku_models import CMP, Cu


class GE_RootSKU(models.Model):
    xcode = models.CharField(max_length=15)
    sku = models.CharField(max_length=150)

    class Meta:
        managed = False
        db_table = '[dbo].[ROOT_REF_SKU]'


class GE_REF_SKU(models.Model):
    root_sku = models.ForeignKey(GE_RootSKU, on_delete=models.PROTECT)
    shipment = models.CharField(max_length=3, null=True)
    translation = models.CharField(max_length=90, null=True)
    open_date = models.DateField(null=True)
    close_date = models.DateField(null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_REF_SKU]'


class GE_PIVOT_SKU(models.Model):
    material = models.CharField(max_length=150)
    ge_sku = models.ForeignKey(GE_REF_SKU, on_delete=models.PROTECT, null=True)
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True)
    last_sales_period = models.DateField(null=True)
    last_stock_period = models.DateField(null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_PIVOT_SKU]'


class GE_REF_CompetingSKU(models.Model):
    rus_description = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_REF_Competing_skus]'


class GE_PIVOT_CompetingSKU(models.Model):
    material = models.TextField()
    ge_competing_sku = models.ForeignKey(GE_REF_CompetingSKU, on_delete=models.PROTECT, null=True)
    root_cmp = models.ForeignKey(CMP, on_delete=models.PROTECT, null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_PIVOT_Competing_skus]'


class GE_REF_Store(models.Model):
    translation = models.CharField(max_length=75)
    channel = models.CharField(max_length=10)
    city = models.CharField(max_length=15, null=True)
    store_status = models.CharField(max_length=10)
    open_date = models.DateField(null=True)
    close_date = models.DateField(null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_REF_Stores]'


class GE_PIVOT_Store(models.Model):
    store_ge = models.CharField(max_length=100)
    ge_store = models.ForeignKey(GE_REF_Store, on_delete=models.PROTECT, null=True)

    class Meta:
        managed = False
        db_table = '[dbo].[GE_PIVOT_Stores]'
