from django.db import models

class KASPI_TMP_Sale(models.Model):
    receive_dt = models.CharField(max_length=255)
    change_dt = models.CharField(max_length=255)
    plan_dt = models.CharField(max_length=255)
    fact_dt = models.CharField(max_length=255)
    material = models.CharField(max_length=255)
    material_desc_kaspi = models.CharField(max_length=255)
    material_desc_own = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    cancellation_reason = models.CharField(max_length=255)
    payment_method = models.CharField(max_length=255)
    shipment_method = models.CharField(max_length=255)
    volume = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    ship_price_cust = models.CharField(max_length=255)
    ship_price_store = models.CharField(max_length=255)
    ship_compensation = models.CharField(max_length=255)

    class Meta:
       managed = False
       db_table = '[17_KASPI].[KASPI_TMP_Sales]'