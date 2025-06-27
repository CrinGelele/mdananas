from django.db import models
from root_service.models import Cu, Tu, TuDescription

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

class KG_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=False)
    material = models.TextField()
    class Meta:
       managed = False
       db_table = '[11_KG].[KG_PIVOT_SKU]'