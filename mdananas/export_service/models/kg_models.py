from django.db import models
from root_service.models import Cu

class KG_TMP_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    store_kg = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    measure_name = models.CharField(max_length=255)
    measure_value = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_TMP_Sales]'

class KG_TMP_Competitor_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    store_kg = models.CharField(max_length=255)
    channel = models.CharField(max_length=255)
    brand = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    measure_name = models.CharField(max_length=255)
    measure_value = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_TMP_Competitors_sales]'

class KG_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=False)
    material = models.TextField()
    is_last_upload = models.BooleanField()
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_PIVOT_SKU]'

class KG_REF_Store(models.Model):
    store_kg = models.TextField()
    chain = models.TextField()
    type = models.TextField()
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_REF_Stores]'

class KG_REF_Competitor_SKU(models.Model):
    brand = models.TextField()
    material = models.TextField()
    category = models.TextField()
    groupname = models.TextField()
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_REF_Competitors_SKU]'