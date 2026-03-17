from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache
from ..forms.uz_forms import *
from ..models.uz_models import *
import pandas as pd
from django.db import connections
from mdananas.idealSchemaEditor import IdealSchemaEditor
from pyxlsb import open_workbook, convert_date
import tempfile
import csv
import os
from numpy import nan
import dateparser
from mdananas.upload_tmp_file import upload_file
from django.db import connections

def main_page(request):
    return HttpResponse("Hello, world!")

def process_sales_file(file, request):
    cache.set(f'uz_sales_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
            dt = dateparser.parse(row['Date'][-10:])
            if pd.isna(row['Volume']) and pd.isna(row['Value']):
                continue
            result.append(UZ_TMP_Sale(
                date_year = dt.year,
                date_month = dt.month,
                chain_name = row['Названия строк'],
                chain_type = row['ТИП ТТ'],
                material = row['Код'],
                volume = 0 if pd.isna(row['Volume']) else row['Volume'],
                value = 0 if pd.isna(row['Value']) else row['Value']
            ))
            cache.set(f'uz_sales_file_progress_{request.session.session_key}', int(index / total_rows * 100), 300)
    cache.set(f'uz_sales_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'uz_sales_file_progress_{request.session.session_key}', 0, 300)
    return result

def process_kidpoint_file(file, request):
    cache.set(f'uz_kidpoint_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
            if pd.isna(row.get('Сумма по полю Проданое кол-во', default=0)) or pd.isna(row.get('Полочная цена', default=0)) or pd.isna(row.get('Живая цена', default=0)):
                 continue
            dt = dateparser.parse(row['День'])
            result.append(UZ_TMP_Sale_Kidpoint(
                date_year = dt.year,
                date_month = dt.month,
                date_day = dt.day,
                material = row['Штрих-код'],
                rus_description = row['Название продукта'],
                volume = row.get('Сумма по полю Проданое кол-во', default=0),
                net_value = row.get('Сумма по полю Проданое кол-во', default=0) * row.get('Полочная цена', default=0),
                gross_value = row.get('Сумма по полю Проданое кол-во', default=0) * row.get('Живая цена', default=0)
            ))
            cache.set(f'uz_kidpoint_file_progress_{request.session.session_key}', int(index / total_rows * 100), 300)
    cache.set(f'uz_kidpoint_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'uz_kidpoint_file_progress_{request.session.session_key}', 0, 300)
    return result

def get_progress(request):
    return JsonResponse({'uz_sales_file_progress': cache.get(f'uz_sales_file_progress_{request.session.session_key}', 0),
                         'uz_sales_file_active': cache.get(f'uz_sales_file_active_{request.session.session_key}', 0),
                         'uz_kidpoint_file_progress': cache.get(f'uz_kidpoint_file_progress_{request.session.session_key}', 0),
                         'uz_kidpoint_file_active': cache.get(f'uz_kidpoint_file_active_{request.session.session_key}', 0)})

def uz_page(request):
    cache.set(f'uz_sales_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'uz_kidpoint_file_active_{request.session.session_key}', 1, 300)
    if 'uz_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('uz_pivot_sku_suo', 'on' if request.GET.get('uz_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    if 'uz_pivot_sku_update' in request.GET:
        response = HttpResponseRedirect(request.path)
        with connections['ideal'].cursor() as cursor:
            cursor.execute("EXEC [10_UZ].[UZ_PROC_Update_Pivot_SKU]")
        return response
    uz_pivot_sku_suo = request.COOKIES.get('uz_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = UZ_PIVOT_SKU.objects.filter(is_last_upload=True) if uz_pivot_sku_suo else UZ_PIVOT_SKU.objects.all()
    existing_chains = UZ_REF_Chain.objects.all().order_by('chain_name')
    existing_channels = UZ_REF_Chain.objects.values_list('channel', flat=True).distinct()
    existing_chains_generalized = UZ_REF_Chain.objects.values_list('chain_generalized', flat=True).distinct()
    existing_comp_sku = UZ_REF_Competing_SKU.objects.all().order_by('material')
    existing_brands = UZ_REF_Competing_SKU.objects.values_list('brand', flat=True).distinct()
    existing_groups = UZ_REF_Competing_SKU.objects.values_list('groupname', flat=True).distinct()
    existing_subgroups = UZ_REF_Competing_SKU.objects.values_list('subgroupname', flat=True).distinct()
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    existing_mix = Mix.objects.all().order_by('xcode_mix')
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'sales':
                    upload_file(process_sales_file(form.cleaned_data['file'], request), UZ_TMP_Sale, '[10_UZ].[UZ_PROC_MERGE_Sales]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('uz_page')})
                case 'kidpoint':
                    upload_file(process_kidpoint_file(form.cleaned_data['file'], request), UZ_TMP_Sale_Kidpoint, '[10_UZ].[UZ_PROC_MERGE_Sales_Kidpoint]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('uz_page')})
                case _:
                    pass
        else:
            form = ChainsRefForm(request.POST)
            if form.is_valid():
                object = UZ_REF_Chain.objects.get(id = form.cleaned_data['chain_id'])
                if form.cleaned_data['channel']:
                    object.channel = form.cleaned_data['channel']
                if form.cleaned_data['general']:
                    object.chain_generalized = form.cleaned_data['general']
                object.save()
            else:
                form = CompSKURefForm(request.POST)
                if form.is_valid():
                    object = UZ_REF_Competing_SKU.objects.get(id = form.cleaned_data['comp_sku_id'])
                    if form.cleaned_data['brand']:
                        object.brand = form.cleaned_data['brand']
                    if form.cleaned_data['group']:
                        object.groupname = form.cleaned_data['group']
                    if form.cleaned_data['subgroup']:
                        object.subgroupname = form.cleaned_data['subgroup']
                    object.save()
                else:
                    form = PivotSKUForm(request.POST)
                    if form.is_valid():
                        object = UZ_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
                        if form.cleaned_data['is_mix']:
                            object.is_mix = True
                            object.root_cu = None
                            object.root_mix = Mix.objects.get(id = form.cleaned_data['root_mix']) if form.cleaned_data['root_mix'] else None
                        else:
                            object.is_mix = False
                            object.root_mix = None
                            object.root_cu = Cu.objects.get(id = form.cleaned_data['root_cu']) if form.cleaned_data['root_cu'] else None
                        object.save()
                    else:
                        print(form.errors)
    return render(request, "export_service/uz_page.html", context={'uz_pivot_sku_suo': uz_pivot_sku_suo, 'existing_pivot_sku': existing_pivot_sku, 'existing_chains': existing_chains,
                                                                   'existing_channels': existing_channels, 'existing_comp_sku': existing_comp_sku, 'existing_brands': existing_brands,
                                                                   'existing_groups': existing_groups, 'existing_subgroups': existing_subgroups, 'existing_chains_generalized': existing_chains_generalized,
                                                                   'existing_cu': existing_cu, 'existing_mix': existing_mix})