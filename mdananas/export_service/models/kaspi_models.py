from django.db import models
from root_service.models.ref_sku_models import Cu, PivotCMP


class KASPI_TMP_Sale(models.Model):
    order_number = models.CharField(max_length=50)
    material = models.CharField(max_length=255)
    receive_dt = models.CharField(max_length=19)
    receive_has_time = models.BooleanField()
    change_dt = models.DateField()
    plan_dt = models.DateField(null=True)
    fact_dt = models.CharField(max_length=19, null=True)
    fact_has_time = models.BooleanField(null=True)
    material_desc_kaspi = models.TextField(null=True)
    material_desc_own = models.TextField(null=True)
    address = models.TextField(null=True)
    status = models.CharField(max_length=64)
    cancellation_reason = models.TextField(null=True)
    payment_method = models.CharField(max_length=255, null=True)
    shipment_method = models.CharField(max_length=255, null=True)
    courier_service = models.CharField(max_length=255, null=True)
    shipment_warehouse = models.CharField(max_length=255, null=True)
    signature_required = models.CharField(max_length=255, null=True)
    volume = models.DecimalField(max_digits=19, decimal_places=3)
    value = models.DecimalField(max_digits=19, decimal_places=2)
    ship_price_cust = models.DecimalField(max_digits=19, decimal_places=2, null=True)
    ship_price_store = models.DecimalField(max_digits=19, decimal_places=2, null=True)
    ship_compensation = models.DecimalField(max_digits=19, decimal_places=2, null=True)

    class Meta:
        managed = False
        db_table = '[17_KASPI].[KASPI_TMP_Sales]'


class KASPI_PIVOT_SKU(models.Model):
    id = models.AutoField(primary_key=True)
    material = models.CharField(max_length=255)
    material_desc_kaspi = models.TextField(null=True)
    material_desc_own = models.TextField(null=True)
    mapping_status = models.CharField(
        max_length=16,
        choices=[('pending', 'Не сопоставлен'), ('own', 'CU'), ('competitor', 'CMP')],
    )
    root_cu = models.ForeignKey(Cu, on_delete=models.PROTECT, null=True)
    root_pivot_sku_cmp = models.ForeignKey(PivotCMP, on_delete=models.PROTECT, null=True)

    class Meta:
        managed = False
        db_table = '[17_KASPI].[KASPI_PIVOT_SKU]'
