from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)
    currency = forms.ChoiceField(choices=[('RUB', 'RUB'), ('BYN', 'BYN'), ('KZT', 'KZT')], required=False)

    def clean(self):
        cleaned_data = super().clean()
        currency = cleaned_data.get('currency') or 'RUB'
        if cleaned_data.get('form_name') in ('by', 'kz'):
            currencies = {'by': ('RUB', 'BYN'), 'kz': ('RUB', 'KZT')}
            if currency not in currencies[cleaned_data['form_name']]:
                self.add_error('currency', 'Недопустимая валюта для выбранной страны.')
        cleaned_data['currency'] = currency
        return cleaned_data

class PivotSKUForm(forms.Form):
    root_cu = forms.IntegerField(required=False)
    is_mix = forms.BooleanField(required=False)
    root_mix = forms.IntegerField(required=False)
    pivot_sku_id = forms.IntegerField()