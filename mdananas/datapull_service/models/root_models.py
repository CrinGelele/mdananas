from django.db import models

class ROOT_TMP_Invoice(models.Model):
    date_year = models.CharField(max_length=255)
    date_month = models.CharField(max_length=255)
    date_day = models.CharField(max_length=255)
    xcode = models.CharField(max_length=255)
    customer = models.CharField(max_length=255)
    shipped_to = models.CharField(max_length=255)
    gsv = models.CharField(max_length=255)
    nsv = models.CharField(max_length=255)
    cu = models.CharField(max_length=255)
    on = models.CharField(max_length=255)
    is_promo = models.CharField(max_length=255)
    contract_conditions = models.CharField(max_length=255)
    price_increase_delay = models.CharField(max_length=255)
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_TMP_Invoices]'

class LOG(models.Model):
    date_time = models.DateTimeField()
    operation_type = models.TextField()
    operation_details = models.TextField()
    records_count = models.IntegerField()
    aggregated_records_count = models.IntegerField()
    class Meta:
        db_table = '[MDANANAS].[dbo].[LOGS_DATAPULL_ROOT]'
        managed = False

class ROOT_REF_Customer(models.Model):
    demand_name = models.TextField()
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_REF_Customers]'

class ROOT_PIVOT_Customer(models.Model):
    erp_name = models.TextField()
    shipped_to = models.TextField()
    root_customer = models.ForeignKey(ROOT_REF_Customer, on_delete=models.PROTECT, null=True)
    class Meta:
       managed = False
       db_table = '[00_ROOT].[ROOT_PIVOT_Customers]'