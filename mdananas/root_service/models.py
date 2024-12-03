from django.db import models
from math import pi

class Supplier(models.Model):
    supplier_name = models.CharField(max_length=50, null=False)
    ownership = models.CharField(max_length=5, null=False)
    currency = models.CharField(max_length=5, null=False)
    class Meta:
       managed = False
       db_table = 'ROOT_REF_SKU_Suppliers'

class Definition(models.Model):
    rus_definition = models.TextField(null=False)
    eng_definition = models.TextField(null=False)
    class Meta:
       managed = False
       db_table = 'ROOT_REF_SKU_Definitions'

class Cu(models.Model):
    xcode_cu = models.CharField(max_length=15, unique=True, null=False)
    ean_cu = models.CharField(max_length=13, null=True)
    root_pd = models.ForeignKey('Definition', on_delete=models.PROTECT, null=True)
    category = models.CharField(max_length=15, null=False)
    groupname = models.CharField(max_length=25, null=False)
    status = models.CharField(max_length=5, null=False)
    type = models.CharField(max_length=1, null=False)
    shelf_life = models.SmallIntegerField(null=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.PROTECT, null=True)
    class Meta:
       managed = False
       db_table = 'ROOT_REF_SKU_CU'

class CuDimensions(models.Model):
    root_cu = models.OneToOneField('Cu', on_delete=models.PROTECT, null=False)
    length = models.FloatField(null=True)
    width = models.FloatField(null=True)
    height = models.FloatField(null=True)
    diameter = models.FloatField(null=True)
    volume = models.FloatField(null=True)
    net_weight = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = 'ROOT_REF_SKU_CU_Dimensions'
