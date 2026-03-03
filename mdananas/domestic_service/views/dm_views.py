from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache
from ..forms.dm_forms import *
from ..models.dm_models import *
import pandas as pd
from django.db import connections
from mdananas.idealSchemaEditor import IdealSchemaEditor
from pyxlsb import open_workbook, convert_date
import tempfile
import csv
import os
import dateparser
import re
from mdananas.upload_tmp_file import upload_file

def main_page(request):
    return HttpResponse("Hello, world!")

def process_by_file(file, request):
    cache.set(f'by_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        dt = pd.to_datetime(row['Дата'], unit='D', origin='1899-12-30')
        result.append(DM_TMP_BY_Sale(
            date_year = dt.year,
            date_month = dt.month,
            date_day = dt.day,
            store_dm = row['КодМагазина'],
            store_name = row['Магазин'],
            material = row['КодТовара'],
            purchase_volume = row['Приходы (с возвратами и перемещениями) ШТ'],
            purchase_value = row['Приходы (с возвратами и перемещениями) ЗЦ руб'],
            volume = row['Товарооборот ШТ'],
            value = row['Товарооборот ФЦ руб'],
            stock = row['Остаток ШТ']
        ))
        cache.set(f'by_file_progress_{request.session.session_key}', int((index + 1) / total_rows * 100), 300) 
    cache.set(f'by_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'by_file_progress_{request.session.session_key}', 0, 300) 
    return result

def process_kz_file(file, request):
    cache.set(f'kz_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        dt = pd.to_datetime(row['Дата'], unit='D', origin='1899-12-30')
        result.append(DM_TMP_KZ_Sale(
            date_year = dt.year,
            date_month = dt.month,
            date_day = dt.day,
            store_dm = row['КодМагазина'],
            store_name = row['Магазин'],
            material = row['КодТовара'],
            purchase_volume = row['Приходы (с возвратами и перемещениями) ШТ'],
            purchase_value = row['Приходы (с возвратами и перемещениями) ЗЦ руб'],
            volume = row['Товарооборот ШТ'],
            value = row['Товарооборот ФЦ руб'],
            stock = row['Остаток ШТ']
        ))
        cache.set(f'kz_file_progress_{request.session.session_key}', int((index + 1) / total_rows * 100), 300) 
    cache.set(f'kz_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'kz_file_progress_{request.session.session_key}', 0, 300) 
    return result

def process_decade_file(file, request):
    pass

def process_implant_file(file, request):
    cache.set(f'implant_file_progress_{request.session.session_key}', 0, 300)
    result = []
    header = {}
    with open_workbook(file) as wb:
        current_row = 0
        total_rows = wb.get_sheet(1).dimension.h
        for row in wb.get_sheet(1).rows():
            current_row += 1
            if current_row == 1:
                for cell in row:
                    header[cell.v] = cell.c
            else:
                object = DM_TMP_RU_Sale()
                for cell in row:
                    match cell.c:
                        case key if key == header.get('Дата'):
                            dt = convert_date(cell.v)
                            object.date_year = dt.year
                            object.date_month = dt.month
                            object.date_day = dt.day
                        case key if key == header.get('КодМагазина ООО'):
                            object.store_dm = cell.v
                        case key if key == header.get('Магазин'):
                            object.store_name = cell.v
                        case key if key == header.get('КодТовара'):
                            object.material = cell.v
                        case key if key == header.get('Приходы от поставщика ШТ'):
                            object.purchase = cell.v
                        case key if key == header.get('Реализация для оплат ШТ'):
                            object.volume = cell.v
                        case key if key == header.get('Товарооборот ЗЦ'):
                            object.purchase_price_value = cell.v
                        case key if key == header.get('Товарооборот АЦ'):
                            object.fact_price_value = cell.v
                        case key if key == header.get('Остаток ШТ'):
                            object.stock = cell.v
                        case key if key == header.get('Товарооборот ФЦ'):
                            object.fc = cell.v
                        case _:
                            pass
                result.append(object)
                cache.set(f'implant_file_progress_{request.session.session_key}', int(current_row / total_rows * 100), 300)
    cache.set(f'implant_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'implant_file_progress_{request.session.session_key}', 0, 300)
    return result

def process_stores_file(file, request):
    cache.set(f'dm_stores_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        result.append(DM_TMP_Store(
            store_dm = row['Завод'],
            store_name = row['Имя'],
            open_date = row['Дата открытия'],
            close_date = row['Дата закрытия'],
            address_city = row['Город'],
            address_street = row['Улица'],
            address_house = row['Номер дома']
        ))
        cache.set(f'dm_stores_file_progress_{request.session.session_key}', int((index + 1) / total_rows * 100), 300)
    cache.set(f'dm_stores_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'dm_stores_file_progress_{request.session.session_key}', 0, 300) 
    return result

def get_latest_clusters(date_year, date_month, date_day):
    query = '''
        WITH ranked_clusters AS (
        SELECT dm_store_id, dm_pivot_sku_id, cluster, DATEFROMPARTS(date_year, date_month, date_day) AS cluster_date,
                ROW_NUMBER() OVER (
                    PARTITION BY dm_store_id, dm_pivot_sku_id 
                    ORDER BY DATEFROMPARTS(date_year, date_month, date_day) DESC
                ) AS rn
            FROM 
                [20_DM].DM_REF_Clusters
            WHERE 
                DATEFROMPARTS(date_year, date_month, date_day) <= DATEFROMPARTS(%s, %s, %s)  -- Фильтр по дате
        )
        SELECT store_dm, material, cluster FROM ranked_clusters A
        LEFT JOIN [20_DM].DM_PIVOT_SKU B ON A.dm_pivot_sku_id = B.id
        LEFT JOIN [20_DM].DM_REF_Stores C ON A.dm_store_id = C.id WHERE  rn = 1;'''
    with connections['ideal'].cursor() as cursor:
        cursor.execute(query, [date_year, date_month, date_day])
        result = cursor.fetchall()
    df = pd.DataFrame(result, columns=["store_dm", "material", "cluster"])
    return df

def process_clusters_file(file, request):
    cache.set(f'dm_clusters_file_progress_{request.session.session_key}', 0, 300)
    date_match = re.search(r'\b\d{2}\.\d{2}\.\d{2,4}\b', file.name)
    date_str = date_match.group()
    dt = dateparser.parse(date_str, date_formats=['%d.%m.%y', '%d.%m.%Y'])
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        result.append(DM_TMP_Cluster(
            date_year = dt.year,
            date_month = dt.month,
            date_day = dt.day,
            material = row['Материал'],
            store_dm = row['Завод'],
            cluster = row['Название подформата магазина'],
            min_balance = row['Мин.неснижаемый запас']
        ))
        cache.set(f'dm_clusters_file_progress_{request.session.session_key}', int((index + 1) / total_rows * 100), 300)
    cache.set(f'dm_clusters_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'dm_clusters_file_progress_{request.session.session_key}', 0, 300) 
    return result

def get_progress(request):
    return JsonResponse({'by_file_progress': cache.get(f'by_file_progress_{request.session.session_key}', 0),
                         'by_file_active': cache.get(f'by_file_active_{request.session.session_key}', 0),
                         'kz_file_progress': cache.get(f'kz_file_progress_{request.session.session_key}', 0),
                         'kz_file_active': cache.get(f'kz_file_active_{request.session.session_key}', 0),
                         'implant_file_progress': cache.get(f'implant_file_progress_{request.session.session_key}', 0),
                         'implant_file_active': cache.get(f'implant_file_active_{request.session.session_key}', 0),
                         'dm_stores_file_progress': cache.get(f'dm_stores_file_progress_{request.session.session_key}', 0),
                         'dm_stores_file_active': cache.get(f'dm_stores_file_active_{request.session.session_key}', 0),
                         'dm_clusters_file_progress': cache.get(f'dm_clusters_file_progress_{request.session.session_key}', 0),
                         'dm_clusters_file_active': cache.get(f'dm_clusters_file_active_{request.session.session_key}', 0),})

def dm_page(request):
    cache.set(f'by_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'kz_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'implant_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'dm_stores_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'dm_clusters_file_active_{request.session.session_key}', 1, 300)
    if 'dm_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('dm_pivot_sku_suo', 'on' if request.GET.get('dm_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    dm_pivot_sku_suo = request.COOKIES.get('dm_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = DM_PIVOT_SKU.objects.filter(is_last_upload=True) if dm_pivot_sku_suo else DM_PIVOT_SKU.objects.all()
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    existing_mix = Mix.objects.all().order_by('xcode_mix')
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'by':
                    upload_file(process_by_file(form.cleaned_data['file'], request), DM_TMP_BY_Sale, '[20_DM].[DM_PROC_MERGE_BY_Sales]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'kz':
                    upload_file(process_kz_file(form.cleaned_data['file'], request), DM_TMP_KZ_Sale, '[20_DM].[DM_PROC_MERGE_KZ_Sales]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'implant':
                    upload_file(process_implant_file(form.cleaned_data['file'], request), DM_TMP_RU_Sale, '[20_DM].[DM_PROC_MERGE_RU_Sales]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'stores':
                    upload_file(process_stores_file(form.cleaned_data['file'], request), DM_TMP_Store, '[20_DM].[DM_PROC_MERGE_Stores]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'clusters':
                    upload_file(process_clusters_file(form.cleaned_data['file'], request), DM_TMP_Cluster, '[20_DM].[DM_PROC_MERGE_Clusters]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case _:
                    pass
        else:
            form = PivotSKUForm(request.POST)
            if form.is_valid():
                object = DM_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
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
    return render(request, "domestic_service/dm_page.html", context={'existing_pivot_sku': existing_pivot_sku, 'existing_cu': existing_cu, 'existing_mix': existing_mix,
                                                                      'dm_pivot_sku_suo': dm_pivot_sku_suo})