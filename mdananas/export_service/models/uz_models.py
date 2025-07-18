from django.db import models
from root_service.models import Cu, Mix

class UZ_TMP_Sale(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    chain_name = models.CharField(max_length=255)
    chain_type = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[10_UZ].[UZ_TMP_Sales]'

class UZ_TMP_Sale_Kidpoint(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_day = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    gross_value = models.CharField(max_length=255)
    net_value = models.CharField(max_length=255)
    rus_description = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[10_UZ].[UZ_TMP_Sales_Kidpoint]'

class UZ_PIVOT_SKU(models.Model):
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True, )
    root_mix = models.ForeignKey(Mix, on_delete=models.PROTECT, null=True)
    material = models.TextField()
    is_last_upload = models.BooleanField()
    is_mix = models.BooleanField()
    class Meta:
       managed = False
       db_table = '[10_UZ].[UZ_PIVOT_SKU]'

class UZ_REF_Chain(models.Model):
    chain_type = models.TextField()
    chain_name = models.TextField()
    chain_class = models.TextField()
    class Meta:
       managed = False
       db_table = '[10_UZ].[UZ_REF_Chains]'

class UZ_REF_Competing_SKU(models.Model):
    material = models.TextField()
    rus_description = models.TextField()
    brand = models.TextField()
    groupname = models.TextField()
    subgroupname = models.TextField()
    class Meta:
       managed = False
       db_table = '[10_UZ].[UZ_REF_Competing_skus]'