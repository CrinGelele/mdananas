from django.db import models
from .root_models import ROOT_PIVOT_Customer
from root_service.models.ref_sku_models import Tu, Cu, Mix

class PRICEM_DATA_INT_Monitoring(models.Model):
    client_code = models.CharField(max_length=30, null=True, blank=True)
    root_tu = models.ForeignKey(Tu, on_delete=models.CASCADE, db_column='root_tu_id', null=True, blank=True)
    root_mix = models.ForeignKey(Mix, on_delete=models.CASCADE, db_column='root_mix_id', null=True, blank=True)

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_DATA_INT_Monitoring]'


class PRICEM_DATA_EXT_Monitoring(models.Model):
    client_code = models.CharField(max_length=30, null=True, blank=True)
    material = models.CharField(max_length=30, null=True, blank=True)
    pricem_description = models.TextField(null=True, blank=True)
    brand = models.CharField(max_length=30, null=True, blank=True)
    category = models.CharField(max_length=30, null=True, blank=True)

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_DATA_EXT_Monitoring]'


class PRICEM_REF_Tags(models.Model):
    tag = models.TextField()

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_REF_Tags]'


class PRICEM_LINK_Tags(models.Model):
    pricem_int_monitoring = models.ForeignKey(PRICEM_DATA_INT_Monitoring, on_delete=models.CASCADE, db_column='pricem_int_monitoring_id', null=True, blank=True)
    pricem_ext_monitoring = models.ForeignKey(PRICEM_DATA_EXT_Monitoring, on_delete=models.CASCADE, db_column='pricem_ext_monitoring_id', null=True, blank=True)
    pricem_tag = models.ForeignKey(PRICEM_REF_Tags, on_delete=models.CASCADE, db_column='pricem_tag_id')

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_LINK_Tags]'


class PRICEM_DATA_Monitoring_Sources(models.Model):
    pricem_int_monitoring = models.ForeignKey(PRICEM_DATA_INT_Monitoring, on_delete=models.CASCADE, db_column='pricem_int_monitoring_id', null=True, blank=True)
    pricem_ext_monitoring = models.ForeignKey(PRICEM_DATA_EXT_Monitoring, on_delete=models.CASCADE, db_column='pricem_ext_monitoring_id', null=True, blank=True)
    url = models.TextField()
    root_pivot_customer = models.ForeignKey(ROOT_PIVOT_Customer, on_delete=models.CASCADE, db_column='root_pivot_customer_id', null=True, blank=True)
    region = models.CharField(max_length=30, null=True, blank=True)
    status = models.SmallIntegerField(null=True, blank=True)
    sale_option = models.CharField(max_length=10, null=True, blank=True)
    formula = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_DATA_Monitoring_Sources]'

class PRICEM_DATA_Source_Offers(models.Model):
    pricem_source = models.ForeignKey(PRICEM_DATA_Monitoring_Sources, on_delete=models.CASCADE, db_column='pricem_source_id')
    currency = models.CharField(max_length=3, null=True, blank=True)
    last_check_date = models.DateTimeField(null=True, blank=True)
    relevance_status = models.SmallIntegerField(null=True, blank=True)
    in_stock = models.BooleanField(null=True, blank=True)
    price = models.FloatField(null=True, blank=True)
    discount = models.FloatField(null=True, blank=True)
    original_currency = models.CharField(max_length=3, null=True, blank=True)
    original_price = models.FloatField(null=True, blank=True)
    offer = models.TextField()

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_DATA_Source_Offers]'


class PRICEM_DATA_Monitoring_Additional_data(models.Model):
    pricem_source = models.ForeignKey(PRICEM_DATA_Monitoring_Sources, on_delete=models.CASCADE, db_column='pricem_source_id')
    header = models.TextField(null=True, blank=True)
    value = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = '[03_PRICEM].[PRICEM_DATA_Monitoring_Additional_data]'