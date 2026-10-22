import re

import pandas as pd
import xlrd
from django.core.cache import cache
from django.db import DatabaseError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse

from ..forms.by_forms import *
from ..models.by_models import *
from mdananas.upload_tmp_file import upload_file


MONTHS = ('январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
          'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь')


def get_file_year(sheet):
    years = set()
    for i in range(min(7, sheet.nrows)):
        for j in range(sheet.ncols):
            value = str(sheet.cell_value(i, j)).lower()
            if any(month in value for month in MONTHS):
                match = re.search(r'\b20\d{2}\b', value)
                if match:
                    years.add(int(match.group()))
    return years.pop() if len(years) == 1 else None


def process_sales_file(file, request, year=None):
    progress_key = f'by_sales_file_progress_{request.session.session_key}'
    cache.set(progress_key, 0, 300)
    book = xlrd.open_workbook(file_contents=file.read(), formatting_info=True)
    sheet = book.sheet_by_index(0)
    df = pd.read_excel(book, header=None, engine='xlrd', dtype={5: str})

    date_year = year or get_file_year(sheet)
    if not date_year:
        raise ValueError('Не удалось определить год. Введите год отчёта под полем загрузки.')
    if df.shape[0] < 9 or df.shape[1] < 18:
        raise ValueError('Формат Excel не соответствует отчёту Беларуси.')

    sku_rows = set(df.index[(pd.to_numeric(df.iloc[:, 5], errors='coerce').notna()) & (df.index >= 8)])
    if not sku_rows:
        raise ValueError('В отчёте не найдены строки с товарами.')

    parents = {}
    locations = {}
    for i in range(6, len(df)):
        info = sheet.rowinfo_map.get(i)
        if info is None:
            continue
        level = info.outline_level
        parents = {k: v for k, v in parents.items() if k < level}
        if i in sku_rows:
            locations[i] = (parents.get(level - 2), parents.get(level - 1))
        parents[level] = i

    result = []
    totals = {month: [0, 0] for month in range(3, 9)}
    for count, i in enumerate(sorted(sku_rows), 1):
        if i not in locations or None in locations[i]:
            raise ValueError('Не удалось определить магазин для одного из товаров.')
        buyer_row, store_row = locations[i]
        store_by = df.iat[store_row, 2]
        material_desc = df.iat[i, 2]
        material = str(df.iat[i, 5]).strip().removesuffix('.0')
        if pd.isna(store_by) or pd.isna(material_desc):
            raise ValueError('В отчёте найден товар без магазина или описания.')

        for month in range(3, 9):
            volume = df.iat[i, 2 * month]
            value = df.iat[i, 2 * month + 1]
            if pd.isna(volume) and pd.isna(value):
                continue
            volume = 0 if pd.isna(volume) else pd.to_numeric(volume, errors='raise')
            value = 0 if pd.isna(value) else pd.to_numeric(value, errors='raise')
            totals[month][0] += float(volume)
            totals[month][1] += float(value)
            result.append(BY_TMP_Sale(
                date_year=date_year,
                date_month=month,
                store_by=str(store_by),
                material=material,
                material_desc=str(material_desc),
                volume=volume,
                purchase_price_value=0,
                fact_price_value=value,
            ))
        cache.set(progress_key, int(count / len(sku_rows) * 100), 300)

    if not result:
        raise ValueError('В файле не найдены продажи.')

    for month in range(3, 9):
        quantity = float(df.iat[6, 2 * month])
        value = float(df.iat[6, 2 * month + 1])
        if abs(totals[month][0] - quantity) > 0.01 or abs(totals[month][1] - value) > 0.01:
            raise ValueError(f'Не совпали итоги за месяц {month}.')
    return result


def get_progress(request):
    return JsonResponse({
        'by_sales_file_progress': cache.get(f'by_sales_file_progress_{request.session.session_key}', 0),
        'by_sales_file_active': cache.get(f'by_sales_file_active_{request.session.session_key}', 0),
    })


def by_page(request):
    cache.set(f'by_sales_file_active_{request.session.session_key}', 0, 300)
    if 'by_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('by_pivot_sku_suo',
                            'on' if request.GET.get('by_pivot_sku_suo') == 'on' else 'off',
                            max_age=86400)
        return response
    by_pivot_sku_suo = request.COOKIES.get('by_pivot_sku_suo', 'on') == 'on'
    existing_pivot_sku = BY_PIVOT_SKU.objects.filter(is_last_upload=True) if by_pivot_sku_suo else BY_PIVOT_SKU.objects.all()
    existing_stores = BY_REF_Store.objects.all().order_by('store_by')
    existing_comp_sku = BY_PIVOT_SKU.objects.filter(by_competitor_sku__isnull=False).select_related('by_competitor_sku').order_by('material')
    existing_cu = Cu.objects.all().order_by('xcode_cu')
    existing_chains = BY_REF_Store.objects.values_list('chain_name', flat=True).distinct().order_by('chain_name')
    existing_channels = BY_REF_Store.objects.values_list('channel', flat=True).distinct().order_by('channel')
    existing_materials = BY_PIVOT_SKU.objects.filter(by_competitor_sku__isnull=True).order_by('material')

    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid() and form.cleaned_data['form_name'] == 'sales':
            active_key = f'by_sales_file_active_{request.session.session_key}'
            cache.set(active_key, 1, 300)
            try:
                records = process_sales_file(form.cleaned_data['file'], request, form.cleaned_data['year'])
                upload_file(records, BY_TMP_Sale, '[15_BY].[BY_PROC_MERGE_Sales]')
                return JsonResponse({'status': 'success', 'redirect_url': reverse('by_page')})
            except (ValueError, xlrd.XLRDError, DatabaseError) as error:
                return JsonResponse({'status': 'error', 'message': str(error)}, status=400)
            finally:
                cache.set(active_key, 0, 300)
        elif 'store_id' in request.POST:
            form = StoreRefForm(request.POST)
            if form.is_valid():
                item = BY_REF_Store.objects.get(id=form.cleaned_data['store_id'])
                if 'chain_name' in request.POST:
                    item.chain_name = form.cleaned_data['chain_name'] or None
                if 'channel' in request.POST:
                    item.channel = form.cleaned_data['channel'] or None
                item.save()
        elif 'comp_sku_id' in request.POST:
            form = CompetitorRefForm(request.POST)
            if form.is_valid():
                item = BY_REF_Competitor_SKU.objects.get(id=form.cleaned_data['comp_sku_id'])
                if 'brand' in request.POST:
                    item.brand = form.cleaned_data['brand'] or None
                if 'category' in request.POST:
                    item.category = form.cleaned_data['category'] or None
                if 'groupname' in request.POST:
                    item.groupname = form.cleaned_data['groupname'] or None
                item.save()
        elif 'add_comp_sku' in request.POST:
            form = CompetitorAddForm(request.POST)
            if form.is_valid():
                item = BY_PIVOT_SKU.objects.get(id=form.cleaned_data['pivot_sku_id'])
                if item.by_competitor_sku_id is None:
                    item.by_competitor_sku = BY_REF_Competitor_SKU.objects.create()
                    item.save(update_fields=['by_competitor_sku'])
                return HttpResponseRedirect(reverse('by_page'))
        elif 'pivot_sku_id' in request.POST:
            form = PivotSKUForm(request.POST)
            if form.is_valid():
                item = BY_PIVOT_SKU.objects.get(id=form.cleaned_data['pivot_sku_id'])
                item.root_cu = Cu.objects.get(id=form.cleaned_data['root_cu']) if form.cleaned_data['root_cu'] else None
                item.save()
        if request.POST.get('form_name') == 'sales':
            return JsonResponse({'status': 'error', 'message': str(form.errors)}, status=400)
        return JsonResponse({'status': 'success'})

    return render(request, 'export_service/by_page.html', context={
        'by_pivot_sku_suo': by_pivot_sku_suo,
        'existing_pivot_sku': existing_pivot_sku,
        'existing_stores': existing_stores,
        'existing_comp_sku': existing_comp_sku,
        'existing_cu': existing_cu,
        'existing_chains': existing_chains,
        'existing_channels': existing_channels,
        'existing_materials': existing_materials,
    })
