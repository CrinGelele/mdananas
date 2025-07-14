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

def main_page(request):
    return HttpResponse("Hello, world!")

def process_by_file(file, request):
    cache.set(f'by_file_progress_{request.session.session_key}', 0, 300)
    months = {
        'янв' : 1, 'фев' : 2, 'мар' : 3, 'апр' : 4, 'май' : 5, 'июн' : 6,
        'июл' : 7, 'авг' : 8, 'сен' : 9, 'окт' : 10, 'ноя' : 11, 'дек' : 12
    }
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        result.append(DM_TMP_BY_Sale(
            date_year = row['Год'],
            date_month = months[row['Месяц']],
            store_dm = row['КодМагазина'],
            store_name = row['Магазин'],
            material = row['КодТовара'],
            purchase = row['Приходы (с возвратами и перемещениями) ШТ'],
            volume = row['Товарооборот ШТ'],
            value = row['Товарооборот ФЦ руб'],
            stock = row['Остаток ШТ']
        ))
        cache.set(f'by_file_progress_{request.session.session_key}', (index + 1) / total_rows * 100, 300) 
    cache.set(f'by_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'by_file_progress_{request.session.session_key}', 0, 300) 
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
                        case _:
                            pass
                result.append(object)
                cache.set(f'implant_file_progress_{request.session.session_key}', int(current_row / total_rows * 100), 300)
    cache.set(f'implant_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'implant_file_progress_{request.session.session_key}', 0, 300)
    return result


def bulk_insert_to_sqlserver(csv_path, model):
    with connections['ideal'].cursor() as cursor:
        cursor.execute(f"""
            BULK INSERT {model._meta.db_table}
            FROM '{csv_path}'
            WITH (
                CODEPAGE = '65001',
                FIRSTROW = 2,
                ROWTERMINATOR = '\r\n',
                FIELDTERMINATOR = ';'
            )
        """)
    if os.path.exists(csv_path):
        os.remove(csv_path)

def upload_file(file_data, model, proc, big=False):
    with connections['ideal'].cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(model)
            if big:
                NETWORK_FOLDER = r"\\hru03\Public\BI\40. ERP data for SQL"
                with tempfile.NamedTemporaryFile(mode='w+', suffix='.csv', encoding='utf-8', dir=NETWORK_FOLDER, delete=False) as tmp_file:
                    writer = csv.writer(tmp_file, delimiter=';', lineterminator='\n')
                    writer.writerow([f.name for f in model._meta.fields])  # Заголовки
                    for obj in file_data:
                        writer.writerow([getattr(obj, f.name) for f in model._meta.fields])
                    tmp_file.flush()
                bulk_insert_to_sqlserver(tmp_file.name.replace(os.sep, '/'), model)
            else:
                model.objects.bulk_create(file_data)
            cursor.execute(f"EXEC {proc}")
            cursor.execute(f"DROP TABLE IF EXISTS {model._meta.db_table}")

def get_progress(request):
    return JsonResponse({'by_file_progress': cache.get(f'by_file_progress_{request.session.session_key}', 0),
                         'by_file_active': cache.get(f'by_file_active_{request.session.session_key}', 0),
                         'implant_file_progress': cache.get(f'implant_file_progress_{request.session.session_key}', 0),
                         'implant_file_active': cache.get(f'implant_file_active_{request.session.session_key}', 0),})

def dm_page(request):
    cache.set(f'by_file_active_{request.session.session_key}', 1, 300)
    cache.set(f'implant_file_active_{request.session.session_key}', 1, 300)
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
                    upload_file(process_by_file(form.cleaned_data['file'], request), DM_TMP_BY_Sale, '[20_DM].[DM_PROC_MERGE_BY_Sales]')
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'implant':
                    upload_file(process_implant_file(form.cleaned_data['file'], request), DM_TMP_RU_Sale, '[20_DM].[DM_PROC_MERGE_RU_Sales]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                case 'decade':
                    #upload_file(process_decade_file(form.cleaned_data['file'], request), DM_TMP_BY_Sale, '[20_DM].[DM_PROC_MERGE_BY_Sales]')
                    #process_decade_file(form.cleaned_data['file'], request)
                    #return JsonResponse({'status': 'success','redirect_url': reverse('dm_page')})
                    pass
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