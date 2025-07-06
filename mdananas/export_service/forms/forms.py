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

class KGRefStoreFrom(forms.Form):
    form_name = forms.CharField(max_length=20)
    form_changed = forms.CharField(max_length=20)
    kg_store_id = forms.CharField()
    chain = forms.CharField()
    type = forms.CharField()

class KGRefCompSKUFrom(forms.Form):
    form_name = forms.CharField(max_length=20)
    form_changed = forms.CharField(max_length=20)
    ref_comp_sku_id = forms.CharField()
    category = forms.CharField(required=False)
    groupname = forms.CharField(required=False)