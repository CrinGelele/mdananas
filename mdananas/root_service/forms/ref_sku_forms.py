from django import forms
from ..models.ref_sku_models import *
from django.forms import formset_factory

class CuForm(forms.Form):
    xcode_cu = forms.CharField()
    ean_cu = forms.CharField(required=False)
    category = forms.CharField()
    groupname = forms.CharField()
    shelf_life = forms.IntegerField(required=False)
    rus_definition = forms.CharField(required=False)
    root_pd = forms.CharField(required=False)
    cons_active = forms.BooleanField(required=False)

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

class CuCustomsInfoForm(forms.ModelForm):
    customs_code = forms.CharField(max_length=10, required=False)
    duty = forms.FloatField(required=False)
    okpd2_code = forms.CharField(max_length=12, required=False)
    vat = forms.FloatField(required=False)
    class Meta:
        model = CuCustomsInfo
        exclude = ["id", "root_cu"]

    def clean_duty(self):
        duty = self.cleaned_data['duty']
        print('huy')
        if duty:
            return duty / 100  # Преобразуем процент в дробь
        return duty
    
    def clean_vat(self):
        vat = self.cleaned_data['vat']
        if vat:
            return vat / 100  # Преобразуем процент в дробь
        return vat

class TuForm(forms.ModelForm):
    xcode_tu = forms.CharField(required=True)
    ean_tu = forms.CharField(required=True)
    status = forms.CharField(required=True)
    type = forms.CharField(required=True)
    cu_in_tu = forms.IntegerField()
    class Meta:
        model = Tu
        exclude = ["id"]

class TuDimensionsForm(forms.ModelForm):
    length = forms.FloatField(required=False)
    width = forms.FloatField(required=False)
    height = forms.FloatField(required=False)
    volume = forms.FloatField(required=False)
    net_weight = forms.FloatField(required=False)
    class Meta:
        model = TuDimensions
        exclude = ["id", "root_tu"]

class TuLogisticsInfoForm(forms.ModelForm):
    tu_per_layer = forms.IntegerField(required=False)
    layers_per_pal = forms.IntegerField(required=False)
    pal_per_truck = forms.IntegerField(required=False)
    gross_weight_pal = forms.FloatField(required=False)
    gross_weight_tu = forms.FloatField(required=False)
    class Meta:
        model = TuLogisticsInfo
        exclude = ["id", "root_tu"]
        
class TuDescriptionForm(forms.ModelForm):
    rus_description = forms.CharField(required=False)
    eng_description = forms.CharField(required=False)
    class Meta:
        model = TuDescription
        fields = ['rus_description', 'eng_description']

class TuOrderInfoForm(forms.ModelForm):
    moq = forms.FloatField(required=False)
    order_inc = forms.FloatField(required=False)
    is_shared = forms.CharField(required=False)
    class Meta:
        model = TuOrderInfo
        fields = ['moq', 'order_inc', 'is_shared']

class MixForm(forms.Form):
    xcode_mix = forms.CharField(required=True)
    ean_mix = forms.CharField(required=False)
    category = forms.CharField(required=False)
    groupname = forms.CharField(required=False)
    status = forms.CharField(required=False)
    mix_in_box = forms.FloatField(required=False)
    rus_definition = forms.CharField(required=False)
    root_pd = forms.CharField(required=False)
    cons_active = forms.BooleanField(required=False)

class MixCompositionForm(forms.ModelForm):
    class Meta:
        model = MixComposition
        fields = ['root_cu', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['root_cu'].queryset = Cu.objects.all().order_by('xcode_cu')
        self.fields['root_cu'].empty_label = ''
        self.fields['root_cu'].required = False
        self.fields['quantity'].required = False


MixCompositionFormSet = formset_factory(MixCompositionForm, extra=1, can_delete=True)

class MixDimensionsForm(forms.ModelForm):
    length = forms.FloatField(required=False)
    width = forms.FloatField(required=False)
    height = forms.FloatField(required=False)
    volume = forms.FloatField(required=False)
    net_weight = forms.FloatField(required=False)
    class Meta:
        model = MixDimensions
        exclude = ["id", "root_mix"]

class MixLogisticsInfoForm(forms.ModelForm):
    tu_per_layer = forms.IntegerField(required=False)
    layers_per_pal = forms.IntegerField(required=False)
    pal_per_truck = forms.IntegerField(required=False)
    gross_weight_pal = forms.FloatField(required=False)
    gross_weight_tu = forms.FloatField(required=False)
    class Meta:
        model = MixLogisticsInfo
        exclude = ["id", "root_mix"]

class MixCustomsInfoForm(forms.ModelForm):
    customs_code = forms.CharField(max_length=10, required=False)
    duty = forms.FloatField(required=False)
    okpd2_code = forms.CharField(max_length=12, required=False)
    vat = forms.FloatField(required=False)
    class Meta:
        model = MixCustomsInfo
        exclude = ["id", "root_mix"]

    def clean_duty(self):
        duty = self.cleaned_data['duty']
        if duty:
            return duty / 100  # Преобразуем процент в дробь
        return duty
    
    def clean_vat(self):
        vat = self.cleaned_data['vat']
        if vat:
            return vat / 100  # Преобразуем процент в дробь
        return vat

class MixDescriptionForm(forms.ModelForm):
    rus_description = forms.CharField(required=False)
    eng_description = forms.CharField(required=False)
    class Meta:
        model = MixDescription
        fields = ['rus_description', 'eng_description']