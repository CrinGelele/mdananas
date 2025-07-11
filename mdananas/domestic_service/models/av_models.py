from django.db import models
from root_service.models import Cu, Mix

class AV_TMP_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_decade = models.CharField(max_length=255)
    store_format = models.CharField(max_length=255)
    store_av = models.CharField(max_length=255)
    matrix_material = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    av_description = models.CharField(max_length=255)
    purchase_price = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[21_AV].[AV_TMP_Sales]'

class AV_TMP_Stock(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_decade = models.CharField(max_length=255)
    store_format = models.CharField(max_length=255)
    store_av = models.CharField(max_length=255)
    matrix_material = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    av_description = models.CharField(max_length=255)
    purchase_price = models.CharField(max_length=255)
    stock = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[21_AV].[AV_TMP_Stock]'

class AV_TMP_Matrix(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_decade = models.CharField(max_length=255)
    store_format = models.CharField(max_length=255)
    store_av = models.CharField(max_length=255)
    matrix_material = models.CharField(max_length=255)
    av_description = models.CharField(max_length=255)
    presence = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[21_AV].[AV_TMP_Matrix]'

class AV_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True, )
    root_mix = models.ForeignKey(Mix, on_delete=models.PROTECT, null=True)
    material = models.TextField()
    av_description = models.TextField()
    is_last_upload = models.BooleanField()
    is_mix = models.BooleanField()
    class Meta:
       managed = False
       db_table = '[21_AV].[AV_PIVOT_SKU]'

class AV_REF_Store(models.Model):
    store_format = models.CharField(max_length=20)
    store_av = models.TextField()
    class Meta:
       managed = False
       db_table = '[21_AV].[AV_REF_Stores]'