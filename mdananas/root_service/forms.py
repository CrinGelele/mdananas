from django import forms
from .models import Cu, CuDimensions

class CuForm(forms.ModelForm):
    class Meta:
        model = Cu
        exclude = ["id", "root_pd", "supplier"]

class CuDimensionsForm(forms.ModelForm):
    length = forms.FloatField(required=False)
    width = forms.FloatField(required=False)
    height = forms.FloatField(required=False)
    diameter = forms.FloatField(required=False)
    volume = forms.FloatField(required=False)
    net_weight = forms.FloatField(required=False)
    class Meta:
        model = CuDimensions
        exclude = ["id", "root_cu"]
