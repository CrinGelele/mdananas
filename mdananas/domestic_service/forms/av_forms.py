from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)

class PivotSKUForm(forms.Form):
    root_cu = forms.IntegerField(required=False)
    is_mix = forms.BooleanField(required=False)
    root_mix = forms.IntegerField(required=False)
    pivot_sku_id = forms.IntegerField()

class StoreRefForm(forms.Form):
    store_format = forms.CharField(required=False)
    store_id = forms.IntegerField()