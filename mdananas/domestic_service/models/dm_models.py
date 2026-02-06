from django.db import models
from root_service.models.ref_sku_models import Cu, Mix

class DM_TMP_BY_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    store_dm = models.CharField(max_length=255)
    store_name = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    purchase_volume = models.CharField(max_length=255)
    purchase_value = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    stock = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_TMP_BY_Sales]'

class DM_TMP_KZ_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    store_dm = models.CharField(max_length=255)
    store_name = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    purchase_volume = models.CharField(max_length=255)
    purchase_value = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    stock = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_TMP_KZ_Sales]'

class DM_TMP_RU_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_day = models.CharField(max_length=255)
    store_dm = models.CharField(max_length=255)
    store_name = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    purchase = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    purchase_price_value = models.CharField(max_length=255)
    fact_price_value = models.CharField(max_length=255)
    stock = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_TMP_RU_Sales]'

class DM_TMP_Store(models.Model):
    store_dm = models.CharField(max_length=255)
    store_name = models.CharField(max_length=255)
    open_date = models.CharField(max_length=255)
    close_date = models.CharField(max_length=255)
    address_city = models.CharField(max_length=255)
    address_street = models.CharField(max_length=255)
    address_house = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_TMP_Stores]'

class DM_TMP_Cluster(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_day = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    store_dm = models.CharField(max_length=255)
    cluster = models.CharField(max_length=255)
    min_balance = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_TMP_Clusters]'

class DM_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True, )
    root_mix = models.ForeignKey(Mix, on_delete=models.PROTECT, null=True)
    material = models.TextField()
    is_last_upload = models.BooleanField()
    is_mix = models.BooleanField()
    class Meta:
       managed = False
       db_table = '[20_DM].[DM_PIVOT_SKU]'