from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)

class ChainsRefForm(forms.Form):
    chain_class = forms.CharField(required=False)
    chain_id = forms.IntegerField()

class CompSKURefForm(forms.Form):
    brand = forms.CharField(required=False)
    group = forms.CharField(required=False)
    subgroup = forms.CharField(required=False)
    comp_sku_id = forms.IntegerField()