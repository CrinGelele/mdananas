from django import forms


class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    year = forms.IntegerField(required=False)
    form_name = forms.CharField(max_length=20)


class PivotSKUForm(forms.Form):
    root_cu = forms.IntegerField(required=False)
    root_cmp = forms.IntegerField(required=False)
    pivot_sku_id = forms.IntegerField()


class StoreRefForm(forms.Form):
    store_id = forms.IntegerField()
    chain_name = forms.CharField(required=False, max_length=55)
    channel = forms.CharField(required=False, max_length=30)
