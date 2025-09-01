from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
from django.urls import reverse
import pandas as pd
from ..forms.root_forms import *
from ..models.root_models import *
import dateparser
from numpy import nan
from mdananas.upload_tmp_file import upload_file
from django.db import connection
from django.core.cache import cache

def process_invoice_file(file, request):
    cache.set(f'root_invoice_file_progress_{request.session.session_key}', 0, 300)
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
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        if index < 5:
            continue
        if df.iloc[index, 0] == 'Итого':
            continue
        inv_object = ROOT_TMP_Invoice()
        inv_object.is_promo = 0
        last_measure = None
        only_nsv_flag = False
        for col in header:
            if col.get('first_lvl') == 'Контрагент':
                inv_object.customer = row.get(col.get('column_name'))
            elif col.get('first_lvl') == 'Артикул':
                inv_object.xcode = row.get(col.get('column_name'))
            elif col.get('first_lvl') == 'Регистратор':
                reg = row.get(col.get('column_name'))
                inv_object.date_year = last_date.year
                inv_object.date_month = last_date.month
                inv_object.date_day = None
                if 'Объект не найден' in reg:
                    only_nsv_flag = True
            if col.get('second_lvl') == 'Грузополучатель':
                inv_object.shipped_to = row.get(col.get('column_name'))
                continue
            if col.get('second_lvl') is not nan:
                last_measure = col.get('second_lvl')
            if (col.get('first_lvl') == 'P1010-3' or col.get('first_lvl') == 'P1010-4') and not (row.get(col.get('column_name')) == ' '):
                inv_object.is_promo = 1
            if col.get('third_lvl') == 'Сумма' and last_measure:
                match last_measure:
                    case 'Штуки':
                        inv_object.cu = row.get(col.get('column_name')) if not only_nsv_flag else 0
                    case 'GSV':
                        inv_object.gsv = row.get(col.get('column_name')) if not only_nsv_flag else 0
                    case 'Total ON':
                        inv_object.on = row.get(col.get('column_name')) if not only_nsv_flag else 0
                    case 'NSV':
                        inv_object.nsv = row.get(col.get('column_name'))
                    case 'Contract conditions':
                        inv_object.contract_conditions = row.get(col.get('column_name')) if not only_nsv_flag else 0
                    case 'Price increase delay':
                        inv_object.price_increase_delay = row.get(col.get('column_name')) if not only_nsv_flag else 0
                    case _:
                        pass
        result.append(inv_object)
        cache.set(f'root_invoice_file_progress_{request.session.session_key}', int(index / total_rows * 100), 300)
    cache.set(f'root_invoice_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'root_invoice_file_progress_{request.session.session_key}', 0, 300)
    return result

def get_progress(request):
    return JsonResponse({'root_invoice_file_progress': cache.get(f'root_invoice_file_progress_{request.session.session_key}', 0),
                         'root_invoice_file_active': cache.get(f'root_invoice_file_active_{request.session.session_key}', 0)})

def main_page(request):
    cache.set(f'root_invoice_file_active_{request.session.session_key}', 1, 300)
    logs = LOG.objects.all().order_by('date_time').reverse()
    pivot_customers = ROOT_PIVOT_Customer.objects.all().order_by('erp_name')
    existing_customers = ROOT_REF_Customer.objects.all().order_by('demand_name')
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_file(process_invoice_file(form.cleaned_data['file'], request), ROOT_TMP_Invoice, '[00_ROOT].[ROOT_PROC_MERGE_Invoices]', big=True)
            return JsonResponse({'status': 'success','redirect_url': reverse('root_main_page')})
        else:
            form = PivotCustomersForm(request.POST)
            if form.is_valid():
                piv_object = ROOT_PIVOT_Customer.objects.get(id=form.cleaned_data.get('piv_customer_id'))
                if form.cleaned_data.get('customer'):
                    piv_object.root_customer = ROOT_REF_Customer.objects.get(id=form.cleaned_data.get('customer'))
                piv_object.save()
    return render(request, 'datapull_service/root_page.html', context={'logs': logs, 'pivot_customers': pivot_customers, 'existing_customers': existing_customers})