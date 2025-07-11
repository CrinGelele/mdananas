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
                material = matrix[i][1],
                av_description = matrix[i][3],
                purchase_price = matrix[i][4],
                volume = matrix[i][j]
            ))
            cache.set(f'av_sales_file_progress_{request.session.session_key}', int(((i - 1) * (df.shape[1] - 6) + (j - 6)) / total_cells * 100), 300)
    cache.set(f'av_sales_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'av_sales_file_progress_{request.session.session_key}', 0, 300)
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
                         'av_sales_file_active': cache.get(f'av_sales_file_active_{request.session.session_key}', 0)})

def av_page(request):
    cache.set(f'av_sales_file_active_{request.session.session_key}', 1, 300)
    if 'av_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('av_pivot_sku_suo', 'on' if request.GET.get('av_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    av_pivot_sku_suo = request.COOKIES.get('av_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = AV_PIVOT_SKU.objects.filter(is_last_upload=True) if av_pivot_sku_suo else AV_PIVOT_SKU.objects.all()
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'sales':
                    upload_file(process_sales_file(form.cleaned_data['file'], request), AV_TMP_Sale, '[21_AV].[AV_PROC_MERGE_Sales]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('av_page')})
                case 'decade':
                    #upload_file(process_decade_file(form.cleaned_data['file'], request), DM_TMP_BY_Sale, '[20_DM].[DM_PROC_MERGE_BY_Sales]')
                    #process_decade_file(form.cleaned_data['file'], request)
                    #return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                    pass
                case _:
                    pass
    else:
        print(0)
    return render(request, "domestic_service/av_page.html", context={'av_pivot_sku_suo': av_pivot_sku_suo, 'existing_pivot_sku': existing_pivot_sku})