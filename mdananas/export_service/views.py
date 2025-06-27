import pandas as pd
import dateparser
from numpy import nan
from mdananas.idealSchemaEditor import IdealSchemaEditor
from django.db import connections, connection
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from .models import *
from .forms import *


def main_page(request):
    return HttpResponse("Hello, world!")

def process_sales_file(file, request):
    print('------------------------hy!')
    cache.set(f'sales_file_processing_active_{request.session.session_key}', 1, 300)
    cache.set(f'sales_file_processing_progress_{request.session.session_key}', 0, 300)
    if 'рабат' in file.name.lower():
        const_store_kg = 'Мама-Детки Таш рабат'
    elif 'плаза' in file.name.lower():
        const_store_kg = 'Мама-Детки Плаза'
    else:
        const_store_kg = None
    df = pd.read_excel(file, header=None)
    total_cells = (df.shape[0] - 10) * (df.shape[1] - 6) 
    matrix = df.values
    result = []
    for i in range(9, df.shape[0] - 1):
        if matrix[i][3] is not nan:
            current_sku = matrix[i][3]
            next_continue_flag = True
            continue
        if next_continue_flag:
            next_continue_flag = False
            continue
        for j in range(6, df.shape[1]):
            date = matrix[4][j - (j + 1) % 7]
            if date != 'Итог':
                dt = dateparser.parse(date, languages=['ru'])
                if matrix[i][j] is not nan:
                    result.append(KG_TMP_Sale(
                        date_year = dt.year,
                        date_month = dt.month,
                        store_kg = matrix[i][5] if not const_store_kg else const_store_kg,
                        channel = 'Частное лицо' if not const_store_kg else matrix[i][5],
                        material = current_sku,
                        measure_name = matrix[6][j],
                        measure_value = matrix[i][j]
                    ))
            progress = int(((i - 10) * (df.shape[1] - 6) + (j - 6)) / total_cells * 100)
            cache.set(f'sales_file_processing_progress_{request.session.session_key}', progress, 300) 
    cache.set(f'sales_file_processing_active_{request.session.session_key}', 0, 300)
    return result

def upload_sales_data(sales_data):
    with connections['ideal'].cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS [11_KG].[KG_TMP_Sales];")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(KG_TMP_Sale)
            KG_TMP_Sale.objects.bulk_create(sales_data)
            cursor.execute("EXEC [11_KG].[KG_PROC_MERGE_Sales]")
    return redirect('kg_page')

def get_upload_progress(request):
    progress = cache.get(f'sales_file_processing_progress_{request.session.session_key}', 0)
    active = cache.get(f'sales_file_processing_active_{request.session.session_key}', 0)
    return JsonResponse({'sales_file_processing_progress': progress, 'sales_file_processing_active': active})

def get_cus_with_desc():
    with connections['ideal'].cursor() as cursor:
        cursor.execute("SELECT DISTINCT A.id, A.xcode_cu, FIRST_VALUE(C.rus_description) OVER (PARTITION BY A.id, A.xcode_cu ORDER BY C.root_tu_id) rus_description FROM [00_ROOT].ROOT_REF_SKU_CU A " \
        "INNER JOIN [00_ROOT].ROOT_REF_SKU_TU B ON A.id = B.root_cu_id " \
        "LEFT JOIN [00_ROOT].ROOT_REF_SKU_TU_Descriptions C ON B.id = C.root_tu_id ORDER BY xcode_cu")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
    return result

def kg_page(request):
    existing_pivot_sku = KG_PIVOT_SKU.objects.all()
    cus_with_desc = get_cus_with_desc()
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'Sales':
                    sales_data = process_sales_file(form.cleaned_data['file'], request)
                    upload_sales_data(sales_data)
                case 'Competitors':
                    pass
                case _:
                    pass
        else:
            form = PivotSKUForm(request.POST)
            if form.is_valid():
                object = KG_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
                object.root_cu = Cu.objects.get(id = form.cleaned_data['root_cu'])
                object.save()
    else:
        form = FileUploadForm()
    return render(request, 'export_service/kg_page.html', context={'form': form, 'existing_pivot_sku': existing_pivot_sku, 'cus_with_desc': cus_with_desc})