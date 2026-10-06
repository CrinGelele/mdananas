from django import forms
from django.core.exceptions import ValidationError

class NewTaskForm(forms.Form):
    time_hour = forms.IntegerField(required=True)
    time_minute = forms.IntegerField(required=True)
    is_active = forms.BooleanField(required=False)

class ActionTaskForm(forms.Form):
    form_name = forms.CharField(required=True)
    task_id = forms.IntegerField(required=True)
    is_active = forms.BooleanField(required=False)

class NewChainForm(forms.Form):
    source_customer = forms.IntegerField(required=False)
    offer = forms.CharField(required=False)
    promoplan_customer = forms.IntegerField(required=False)
    additional_seller = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        source = cleaned.get('source_customer')
        off = cleaned.get('offer')
        promoplan = cleaned.get('promoplan_customer')
        add = cleaned.get('additional_seller')

        if not source and not off and not promoplan and not add:
            raise ValidationError('One field must be non-empty')

        return cleaned

class ActionChainForm(forms.Form):
    form_name = forms.CharField(required=True)
    chain_id = forms.IntegerField(required=True)

class UpdateExtMonitoringForm(forms.Form):
    ext_monitoring_id = forms.IntegerField(required=True)
    root_cmp = forms.IntegerField(required=True)

class UpdateIntMonitoringForm(forms.Form):
    root_tu = forms.IntegerField(required=False)
    is_mix = forms.BooleanField(required=False)
    root_mix = forms.IntegerField(required=False)
    int_monitoring_id = forms.IntegerField()