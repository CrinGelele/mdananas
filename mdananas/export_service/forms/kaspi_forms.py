from django import forms
from root_service.models.ref_sku_models import Cu, CMP


class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')


class PivotSKUForm(forms.Form):
    pivot_sku_id = forms.IntegerField()
    root_cu = forms.ModelChoiceField(queryset=Cu.objects.using('ideal').all(), required=False)
    root_cmp = forms.ModelChoiceField(queryset=CMP.objects.using('ideal').all(), required=False)
