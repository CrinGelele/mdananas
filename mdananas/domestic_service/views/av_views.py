from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache
from ..forms.av_forms import *
from ..models.av_models import *
import pandas as pd
from django.db import connections
from mdananas.idealSchemaEditor import IdealSchemaEditor
from pyxlsb import open_workbook, convert_date
import tempfile
import csv
import os
from numpy import nan
import dateparser

def main_page(request):
    return HttpResponse("Hello, world!")

def process_sales_file(file, request):
    cache.set(f'av_sales_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=None)
    matrix = df.values
    result = []
    dt = dateparser.parse(str(file.name)[-15:-5])
    total_cells = (df.shape[0] - 1) * (df.shape[1] - 6)
    for i in range(1, df.shape[0]):
        for j in range(6, df.shape[1]):
            if matrix[i][j] is nan:
                continue
            format_point = str(matrix[0][j]).find(' ')
            result.append(AV_TMP_Sale(
                date_year = dt.year,
                date_month = dt.month,
                date_decade = round(dt.day / 10),
                store_format = str(matrix[0][j])[0 : format_point],
                store_av = matrix[0][j],
                matrix_material = matrix[i][0],
                material = matrix[i][1],
                av_description = matrix[i][3],
                purchase_price = matrix[i][4],
                volume = matrix[i][j]
            ))
            cache.set(f'av_sales_file_progress_{request.session.session_key}', int(((i - 1) * (df.shape[1] - 6) + (j - 6)) / total_cells * 100), 300)
    cache.set(f'av_sales_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'av_sales_file_progress_{request.session.session_key}', 0, 300)
    return result

def process_stock_file(file, request):
    cache.set(f'av_stock_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=None)
    matrix = df.values
    result = []
    dt = dateparser.parse(str(file.name)[-15:-5])
    total_cells = (df.shape[0] - 1) * (df.shape[1] - 7)
    for i in range(1, df.shape[0]):
        for j in range(7, df.shape[1]):
            if matrix[i][j] is nan:
                continue
            format_point = str(matrix[0][j]).find(' ')
            result.append(AV_TMP_Stock(
                date_year = dt.year,
                date_month = dt.month,
                date_decade = round(dt.day / 10),
                store_format = str(matrix[0][j])[0 : format_point],
                store_av = matrix[0][j],
                matrix_material = matrix[i][0],
                material = matrix[i][1],
                av_description = matrix[i][2],
                purchase_price = matrix[i][5],
                stock = matrix[i][j]
            ))
            cache.set(f'av_stock_file_progress_{request.session.session_key}', int(((i - 1) * (df.shape[1] - 7) + (j - 7)) / total_cells * 100), 300)
    cache.set(f'av_stock_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'av_stock_file_progress_{request.session.session_key}', 0, 300)
    return result

def process_matrix_file(file, request):
    cache.set(f'av_matrix_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=None)
    matrix = df.values
    result = []
    dt = dateparser.parse(str(file.name)[-15:-5])
    total_cells = (df.shape[0] - 1) * (df.shape[1] - 3)
    for i in range(1, df.shape[0]):
        for j in range(3, df.shape[1]):
            if matrix[i][j] is nan:
                continue
            format_point = str(matrix[0][j]).find(' ')
            result.append(AV_TMP_Matrix(
                date_year = dt.year,
                date_month = dt.month,
                date_decade = round(dt.day / 10),
                store_format = str(matrix[0][j])[0 : format_point],
                store_av = matrix[0][j],
                matrix_material = matrix[i][0],
                av_description = matrix[i][1],
                presence = 1
            ))
            cache.set(f'av_matrix_file_progress_{request.session.session_key}', int(((i - 1) * (df.shape[1] - 3) + (j - 3)) / total_cells * 100), 300)
    cache.set(f'av_matrix_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'av_matrix_file_progress_{request.session.session_key}', 0, 300)
    return result

def upload_file(file_data, model, proc):
    with connections['ideal'].cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(model)
            model.objects.bulk_create(file_data)
            cursor.execute(f"EXEC {proc}")
            cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")

def get_progress(request):
    return JsonResponse({'av_sales_file_progress': cache.get(f'av_sales_file_progress_{request.session.session_key}', 0),
                         'av_sales_file_active': cache.get(f'av_sales_file_active_{request.session.session_key}', 0),
                         'av_stock_file_progress': cache.get(f'av_stock_file_progress_{request.session.session_key}', 0),
                         'av_stock_file_active': cache.get(f'av_stock_file_active_{request.session.session_key}', 0),
                         'av_matrix_file_progress': cache.get(f'av_matrix_file_progress_{request.session.session_key}', 0),
                         'av_matrix_file_active': cache.get(f'av_matrix_file_active_{request.session.session_key}', 0)})

def av_page(request):
    cache.set(f'av_sales_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'av_stock_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'av_matrix_file_active_{request.session.session_key}', 1, 300)
    if 'av_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('av_pivot_sku_suo', 'on' if request.GET.get('av_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    av_pivot_sku_suo = request.COOKIES.get('av_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = AV_PIVOT_SKU.objects.filter(is_last_upload=True) if av_pivot_sku_suo else AV_PIVOT_SKU.objects.all()
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    existing_mix = Mix.objects.all().order_by('xcode_mix')
    existing_stores = AV_REF_Store.objects.all()
    existing_formats = AV_REF_Store.objects.values_list('store_format', flat=True).distinct()
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'sales':
                    upload_file(process_sales_file(form.cleaned_data['file'], request), AV_TMP_Sale, '[21_AV].[AV_PROC_MERGE_Sales]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('av_page')})
                case 'stock':
                    upload_file(process_stock_file(form.cleaned_data['file'], request), AV_TMP_Stock, '[21_AV].[AV_PROC_MERGE_Stock]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('av_page')})
                case 'matrix':
                    upload_file(process_matrix_file(form.cleaned_data['file'], request), AV_TMP_Matrix, '[21_AV].[AV_PROC_MERGE_Matrix]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('av_page')})
                case _:
                    pass
        else:
            form = PivotSKUForm(request.POST)
            if form.is_valid():
                object = AV_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
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
        print(0)
    return render(request, "domestic_service/av_page.html", context={'av_pivot_sku_suo': av_pivot_sku_suo, 'existing_pivot_sku': existing_pivot_sku,
                                                                     'existing_cu': existing_cu, 'existing_mix': existing_mix,
                                                                     'existing_stores': existing_stores, 'existing_formats': existing_formats})