import pandas as pd
import dateparser
from numpy import nan
from mdananas.idealSchemaEditor import IdealSchemaEditor
from django.db import connections
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
import Levenshtein
import json
from ..models.kg_models import *
from ..forms.kg_forms import *

def main_page(request):
    return HttpResponse("Hello, world!")

def process_sales_file(file, request):
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

def process_competitors_file(file, request):
    cache.set(f'competitors_file_processing_active_{request.session.session_key}', 1, 300)
    cache.set(f'competitors_file_processing_progress_{request.session.session_key}', 0, 300)
    if 'рабат' in file.name.lower():
        const_store_kg = 'Мама-Детки Таш рабат'
    elif 'плаза' in file.name.lower():
        const_store_kg = 'Мама-Детки Плаза'
    else:
        const_store_kg = None
    df = pd.read_excel(file, header=None)
    total_cells = (df.shape[0] - 9) * (df.shape[1] - 4) 
    matrix = df.values
    result = []
    for i in range(8, df.shape[0] - 1):
        if matrix[i][2] is not nan:
            current_brand = matrix[i][2]
            continue
        for j in range(4, df.shape[1]):
            date = matrix[4][j - (j + 2) % 6]
            if date != 'Итог':
                dt = dateparser.parse(date, languages=['ru'])
                if matrix[i][j] is not nan:
                    result.append(KG_TMP_Competitor_Sale(
                        date_year = dt.year,
                        date_month = dt.month,
                        store_kg = const_store_kg,
                        channel = 'Частное лицо',
                        brand = current_brand,
                        material = matrix[i][3],
                        measure_name = matrix[6][j],
                        measure_value = matrix[i][j]
                    ))
                    progress = int(((i - 8) * (df.shape[1] - 4) + (j - 4)) / total_cells * 100)
                    cache.set(f'competitors_file_processing_progress_{request.session.session_key}', progress, 300) 
    cache.set(f'competitors_file_processing_active_{request.session.session_key}', 0, 300)
    return result

def upload_sales_data(sales_data):
    with connections['ideal'].cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS [11_KG].[KG_TMP_Sales];")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(KG_TMP_Sale)
            KG_TMP_Sale.objects.bulk_create(sales_data)
            cursor.execute("EXEC [11_KG].[KG_PROC_MERGE_Sales]")
            cursor.execute("DROP TABLE IF EXISTS [11_KG].[KG_TMP_Sales];")

def upload_competitors_data(competitors_data):
    with connections['ideal'].cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS [11_KG].[KG_TMP_Competitors_sales];")
        with IdealSchemaEditor(connection=connections['ideal']) as schema_editor:
            schema_editor.create_model(KG_TMP_Competitor_Sale)
            KG_TMP_Competitor_Sale.objects.bulk_create(competitors_data)
            cursor.execute("EXEC [11_KG].[KG_PROC_MERGE_Competitors_Sales]")
            cursor.execute("DROP TABLE IF EXISTS [11_KG].[KG_TMP_Competitors_sales];")

def get_upload_progress(request):
    return JsonResponse({'sales_file_processing_progress': cache.get(f'sales_file_processing_progress_{request.session.session_key}', 0),
                         'sales_file_processing_active': cache.get(f'sales_file_processing_active_{request.session.session_key}', 0),
                         'competitors_file_processing_progress': cache.get(f'competitors_file_processing_progress_{request.session.session_key}', 0),
                         'competitors_file_processing_active': cache.get(f'competitors_file_processing_active_{request.session.session_key}', 0)})

def get_cus_with_desc():
    with connections['ideal'].cursor() as cursor:
        cursor.execute("SELECT DISTINCT A.id, A.xcode_cu, FIRST_VALUE(C.rus_description) OVER (PARTITION BY A.id, A.xcode_cu ORDER BY C.root_tu_id) rus_description FROM [00_ROOT].ROOT_REF_SKU_CU A " \
        "INNER JOIN [00_ROOT].ROOT_REF_SKU_TU B ON A.id = B.root_cu_id " \
        "LEFT JOIN [00_ROOT].ROOT_REF_SKU_TU_Descriptions C ON B.id = C.root_tu_id ORDER BY xcode_cu")
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        result = [dict(zip(columns, row)) for row in rows]
    return result

def predict_xcode_cu(object):
    cus_with_desc = get_cus_with_desc()
    result = None
    max_c = -1
    for cu in cus_with_desc:
        c = Levenshtein.ratio(cu['rus_description'], object.material)
        if c >= max_c:
            max_c = c
            result = cu
    return result['id']

def kg_page_save_stores(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        stores_data = data.get('forms', []) 
        if not isinstance(stores_data, list):
            return JsonResponse({'error': 'Expected list of stores'}, status=400)
        for store in stores_data:
            form = KGRefStoreFrom(store)
            if form.is_valid():
                object = KG_REF_Store.objects.get(id=form.cleaned_data['kg_store_id'])
                object.chain = form.cleaned_data['chain']
                object.type = form.cleaned_data['type']
                object.save()
    return JsonResponse({'status': 'success','redirect_url': reverse('kg_page')})

def kg_page_save_competitors_sku(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        comp_data = data.get('forms', []) 
        if not isinstance(comp_data, list):
            return JsonResponse({'error': 'Expected list of comp skus'}, status=400)
        for sku in comp_data:
            form = KGRefCompSKUFrom(sku)
            if form.is_valid():
                object = KG_REF_Competitor_SKU.objects.get(id=form.cleaned_data['ref_comp_sku_id'])
                object.category = form.cleaned_data['category']
                object.groupname = form.cleaned_data['groupname']
                object.save()
            else:
                print(form.errors)
    return JsonResponse({'status': 'success','redirect_url': reverse('kg_page')})

def kg_page(request):
    if 'kg_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('kg_pivot_sku_suo', 'on' if request.GET.get('kg_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    kg_pivot_sku_suo = request.COOKIES.get('kg_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = KG_PIVOT_SKU.objects.filter(is_last_upload=True) if kg_pivot_sku_suo else KG_PIVOT_SKU.objects.all()
    existing_ref_stores = KG_REF_Store.objects.all().order_by('chain', 'type')
    existing_chains = KG_REF_Store.objects.values_list('chain', flat=True).distinct()
    existing_types = KG_REF_Store.objects.values_list('type', flat=True).distinct()
    cus_with_desc = get_cus_with_desc()
    existing_ref_competitors_sku = KG_REF_Competitor_SKU.objects.all().order_by('category', 'groupname')
    existing_categories = KG_REF_Competitor_SKU.objects.values_list('category', flat=True).distinct()
    existing_groupnames = KG_REF_Competitor_SKU.objects.values_list('groupname', flat=True).distinct()
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'Sales':
                    sales_data = process_sales_file(form.cleaned_data['file'], request)
                    upload_sales_data(sales_data)
                    return JsonResponse({'status': 'success','redirect_url': reverse('kg_page')})
                case 'Competitors':
                    competitors_data = process_competitors_file(form.cleaned_data['file'], request)
                    upload_competitors_data(competitors_data)
                    return JsonResponse({'status': 'success','redirect_url': reverse('kg_page')})
                case _:
                    pass
        else:
            form = PivotSKUForm(request.POST)
            if form.is_valid():
                object = KG_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
                object.root_cu = Cu.objects.get(id = form.cleaned_data['root_cu'])
                object.save()
            else:
                form = PredictPivotSKUForm(request.POST)
                if form.is_valid():
                    object = KG_PIVOT_SKU.objects.get(id = form.cleaned_data['pivot_sku_id'])
                    predicted_cu_id = predict_xcode_cu(object)
                    object.root_cu = Cu.objects.get(id = predicted_cu_id)
                    object.save()
                    response = HttpResponseRedirect(request.path)
                    if 'scroll_position' in request.POST:
                        response.set_cookie('scroll_pos', request.POST['scroll_position'], max_age=86400)
                    return response
    else:
        form = FileUploadForm()
    return render(request, 'export_service/kg_page.html', context={'form': form, 'existing_pivot_sku': existing_pivot_sku, 'cus_with_desc': cus_with_desc,
                                                                   'kg_pivot_sku_suo': kg_pivot_sku_suo, 'existing_ref_stores': existing_ref_stores,
                                                                   'existing_chains': existing_chains, 'existing_types': existing_types,
                                                                   'existing_ref_competitors_sku': existing_ref_competitors_sku, 'existing_categories': existing_categories, 'existing_groupnames': existing_groupnames})