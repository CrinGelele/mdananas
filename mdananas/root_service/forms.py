from django import forms
from .models import Cu

class CuForm(forms.ModelForm):
    class Meta:
        model = Cu
        exclude = ["id", "root_pd", "supplier"]
