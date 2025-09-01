from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
import pandas as pd
from ..forms.root_forms import *
from ..models.root_models import *
import dateparser
from numpy import nan
from mdananas.upload_tmp_file import upload_file
from django.db import connection

def process_invoice_file(file, request):
    result = []
    df = pd.read_excel(file, skiprows=3, header=None)
    last_date = dateparser.parse(df.iloc[0, 2][-10:])
    header = []
    for index, column in enumerate(df.columns):
        header.append({
            'column_name': column,
            'first_lvl': df.iloc[2, index],
            'second_lvl': df.iloc[3, index],
            'third_lvl': df.iloc[4, index]
        })
    for index, row in df.iterrows():
        if index < 5:
            continue
        if df.iloc[index, 0] == 'Итого':
            continue
        inv_object = ROOT_TMP_Invoice()
        last_measure = None
        for col in header:
            if col.get('first_lvl') == 'Контрагент':
                inv_object.customer = row.get(col.get('column_name'))
            elif col.get('first_lvl') == 'Артикул':
                inv_object.xcode = row.get(col.get('column_name'))
            elif col.get('first_lvl') == 'Регистратор':
                reg = row.get(col.get('column_name'))
                if 'Объект не найден' in reg:
                    inv_object.date_year = last_date.year
                    inv_object.date_month = last_date.month
                    inv_object.date_day = last_date.day
                else:
                    current_date = dateparser.parse(reg[-19: -9])
                    inv_object.date_year = current_date.year
                    inv_object.date_month = current_date.month
                    inv_object.date_day = current_date.day
            if col.get('second_lvl') is not nan:
                last_measure = col.get('second_lvl')
            if col.get('third_lvl') == 'Сумма' and last_measure:
                match last_measure:
                    case 'Штуки':
                        inv_object.cu = row.get(col.get('column_name'))
                    case 'GSV':
                        inv_object.gsv = row.get(col.get('column_name'))
                    case 'ISV':
                        inv_object.isv = row.get(col.get('column_name'))
                    case 'NSV':
                        inv_object.nsv = row.get(col.get('column_name'))
                    case 'Contract conditions':
                        inv_object.contract_conditions = row.get(col.get('column_name'))
                    case 'Price increase delay':
                        inv_object.price_increase_delay = row.get(col.get('column_name'))
                    case _:
                        pass
        result.append(inv_object)
    return result

def main_page(request):
    logs = LOG.objects.all().order_by('date_time').reverse()
    pivot_customers = ROOT_PIVOT_Customer.objects.all().order_by('erp_name')
    existing_customers = ROOT_REF_Customer.objects.all().order_by('demand_name')
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_file(process_invoice_file(form.cleaned_data['file'], request), ROOT_TMP_Invoice, '[00_ROOT].[ROOT_PROC_MERGE_Invoices]')
        else:
            form = PivotCustomersForm(request.POST)
            if form.is_valid():
                piv_object = ROOT_PIVOT_Customer.objects.get(id=form.cleaned_data.get('piv_customer_id'))
                if form.cleaned_data.get('customer'):
                    piv_object.root_customer = ROOT_REF_Customer.objects.get(id=form.cleaned_data.get('customer'))
                piv_object.save()
    return render(request, 'datapull_service/root_page.html', context={'logs': logs, 'pivot_customers': pivot_customers, 'existing_customers': existing_customers})