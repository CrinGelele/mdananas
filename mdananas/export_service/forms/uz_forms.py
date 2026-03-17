from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)

class ChainsRefForm(forms.Form):
    channel = forms.CharField(required=False)
    general = forms.CharField(required=False)
    chain_id = forms.IntegerField()

class CompSKURefForm(forms.Form):
    brand = forms.CharField(required=False)
    group = forms.CharField(required=False)
    subgroup = forms.CharField(required=False)
    comp_sku_id = forms.IntegerField()

class PivotSKUForm(forms.Form):
    root_cu = forms.IntegerField(required=False)
    is_mix = forms.BooleanField(required=False)
    root_mix = forms.IntegerField(required=False)
    pivot_sku_id = forms.IntegerField()