from django import forms


class FileUploadForm(forms.Form):
    file = forms.FileField(label='Файл')


class MappingForm(forms.Form):
    pivot_id = forms.IntegerField(min_value=1)
    ref_id = forms.IntegerField(min_value=1)


class SkuCardFields(forms.Form):
    shipment = forms.CharField(max_length=3, required=False)
    translation = forms.CharField(max_length=90, required=False)
    open_date = forms.DateField(required=False)
    close_date = forms.DateField(required=False)


class CuMappingForm(SkuCardFields):
    pivot_id = forms.IntegerField(min_value=1)
    root_cu_id = forms.IntegerField(min_value=1)
    ref_id = forms.IntegerField(required=False, min_value=1)
    root_sku_id = forms.IntegerField(required=False, min_value=1)


class SkuRefForm(SkuCardFields):
    ref_id = forms.IntegerField(required=False, min_value=1)
    root_sku_id = forms.IntegerField(min_value=1)


class StoreRefForm(forms.Form):
    ref_id = forms.IntegerField(required=False, min_value=1)
    translation = forms.CharField(max_length=75)
    channel = forms.CharField(max_length=10)
    city = forms.CharField(max_length=15, required=False)
    store_status = forms.CharField(max_length=10)
    open_date = forms.DateField(required=False)
    close_date = forms.DateField(required=False)
