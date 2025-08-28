from django.db import models

class Supplier(models.Model):
    supplier_name = models.CharField(max_length=50, null=False)
    ownership = models.CharField(max_length=5, null=False)
    currency = models.CharField(max_length=5, null=False)
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_Suppliers]'

class Definition(models.Model):
    rus_definition = models.TextField(null=False)
    eng_definition = models.TextField(null=True)
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_Definitions]'

class Cu(models.Model):
    xcode_cu = models.CharField(max_length=15, unique=True, null=False)
    ean_cu = models.CharField(max_length=13, null=True)
    root_pd = models.ForeignKey('Definition', on_delete=models.PROTECT, null=True)
    category = models.CharField(max_length=15, null=False)
    groupname = models.CharField(max_length=25, null=False)
    shelf_life = models.SmallIntegerField(null=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.PROTECT, null=True)

    def __str__(self):
        return self.xcode_cu

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_CU]'

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
       db_table = '[00_ROOT].[ROOT_REF_SKU_CU_Dimensions]'

class CuCustomsInfo(models.Model):
    root_cu = models.OneToOneField('Cu', on_delete=models.PROTECT, null=False)
    customs_code = models.CharField(max_length=10)
    duty = models.FloatField(null=True)
    okpd2_code = models.CharField(max_length=10)
    vat = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_CU_Customs_info]'

class Tu(models.Model):
    xcode_tu = models.CharField(max_length=15, unique=True, null=False)
    root_cu = models.ForeignKey('Cu', on_delete=models.PROTECT, null=False, related_name='tus')
    ean_tu = models.CharField(max_length=14, null=True)
    status = models.CharField(max_length=5, null=False)
    type = models.CharField(max_length=1, null=False)
    cu_in_tu = models.IntegerField()
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_TU]'

class TuDimensions(models.Model):
    root_tu = models.OneToOneField('Tu', on_delete=models.PROTECT, null=False)
    length = models.FloatField(null=True)
    width = models.FloatField(null=True)
    height = models.FloatField(null=True)
    volume = models.FloatField(null=True)
    net_weight = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_TU_Dimensions]'

class TuLogisticsInfo(models.Model):
    root_tu = models.OneToOneField('Tu', on_delete=models.PROTECT, null=False)
    tu_per_layer = models.IntegerField(null=True)
    layers_per_pal = models.IntegerField(null=True)
    pal_per_truck = models.IntegerField(null=True)
    gross_weight_pal = models.FloatField(null=True)
    gross_weight_tu = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_TU_Logistics_info]'

class TuDescription(models.Model):
    root_tu = models.ForeignKey('Tu', on_delete=models.PROTECT, null=False, related_name='desc')
    rus_description = models.TextField(null=True)
    eng_description = models.TextField(null=True)
    class Meta:
        managed = False
        db_table = '[00_ROOT].[ROOT_REF_SKU_TU_Descriptions]'

class TuOrderInfo(models.Model):
    root_tu = models.ForeignKey('Tu', on_delete=models.PROTECT, null=False)
    moq = models.FloatField(null=True)
    order_inc = models.FloatField(null=True)
    is_shared = models.CharField(max_length=15, null=True)
    class Meta:
        managed = False
        db_table = '[00_ROOT].[ROOT_REF_SKU_TU_Order_info]'

class Mix(models.Model):
    xcode_mix = models.CharField(max_length=15, unique=True, null=False)
    ean_mix = models.CharField(max_length=14, null=True)
    root_pd = models.ForeignKey('Definition', on_delete=models.PROTECT, null=True)
    category = models.CharField(max_length=15, null=False)
    groupname = models.CharField(max_length=25, null=False)
    status = models.CharField(max_length=5, null=False)
    mix_in_box = models.IntegerField()
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_MIX]'

class MixComposition(models.Model):
    root_cu = models.ForeignKey('Cu', on_delete=models.PROTECT, null=False)
    root_mix = models.ForeignKey('Mix', on_delete=models.PROTECT, null=False)
    quantity = models.IntegerField(null=True)
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_MIX_Compositions]'

class MixDimensions(models.Model):
    root_mix = models.OneToOneField('Mix', on_delete=models.PROTECT, null=False)
    length = models.FloatField(null=True)
    width = models.FloatField(null=True)
    height = models.FloatField(null=True)
    volume = models.FloatField(null=True)
    net_weight = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_MIX_Dimensions]'

class MixLogisticsInfo(models.Model):
    root_mix = models.OneToOneField('Mix', on_delete=models.PROTECT, null=False)
    tu_per_layer = models.IntegerField(null=True)
    layers_per_pal = models.IntegerField(null=True)
    pal_per_truck = models.IntegerField(null=True)
    gross_weight_pal = models.FloatField(null=True)
    gross_weight_tu = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_MIX_Logistics_info]'

class MixCustomsInfo(models.Model):
    root_mix = models.OneToOneField('Mix', on_delete=models.PROTECT, null=False)
    customs_code = models.CharField(max_length=10)
    duty = models.FloatField(null=True)
    okpd2_code = models.CharField(max_length=10)
    vat = models.FloatField(null=True)

    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_SKU_MIX_Customs_info]'

class MixDescription(models.Model):
    root_mix = models.ForeignKey('Mix', on_delete=models.PROTECT, null=False, related_name='desc')
    rus_description = models.TextField(null=True)
    eng_description = models.TextField(null=True)
    class Meta:
        managed = False
        db_table = '[00_ROOT].[ROOT_REF_SKU_MIX_Descriptions]'