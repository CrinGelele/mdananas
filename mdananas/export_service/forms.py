from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)

class PivotSKUForm(forms.Form):
    form_name = forms.CharField(max_length=20)
    root_cu = forms.IntegerField()
    pivot_sku_id = forms.IntegerField()

class PredictPivotSKUForm(forms.Form):
    form_name = forms.CharField(max_length=20)
    pivot_sku_id = forms.IntegerField()

class KgRefStoreForm(forms.Form):
    form_name = forms.CharField(max_length=20)
    kg_store_id = forms.IntegerField()
    chain = forms.CharField(max_length=50)
    type = forms.CharField(max_length=50)