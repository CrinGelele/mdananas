from django import forms

class FileUploadForm(forms.Form):
    file = forms.FileField(label='Выберите файл')
    form_name = forms.CharField(max_length=20)

class PivotCustomersForm(forms.Form):
    piv_customer_id = forms.IntegerField(required=False)
    customer = forms.IntegerField(required=False)