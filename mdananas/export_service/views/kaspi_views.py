from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.core.cache import cache
import pandas as pd
from django.db import connections
from mdananas.idealSchemaEditor import IdealSchemaEditor
from numpy import nan
import dateparser
from mdananas.upload_tmp_file import upload_file
from export_service.forms.kaspi_forms import FileUploadForm
from export_service.models.kaspi_models import KASPI_TMP_Sale

def process_sales_file(file, request):
    cache.set(f'kaspi_sales_file_progress_{request.session.session_key}', 0, 300)
    df = pd.read_excel(file, header=0)
    result = []
    total_rows = df.shape[0]
    for index, row in df.iterrows():
        receive_dt = dateparser.parse(str(row.get('Дата поступления заказа')))
        change_dt = dateparser.parse(str(row.get('Дата изменения статуса')))
        plan_dt = dateparser.parse(str(row.get('Плановая дата передачи курьеру')))
        fact_dt = dateparser.parse(str(row.get('Фактическая дата комплектации')))
        result.append(KASPI_TMP_Sale(
            receive_dt = receive_dt,
            change_dt = change_dt,
            plan_dt = plan_dt,
            fact_dt = fact_dt,
            material = row.get('Артикул'), 
            material_desc_kaspi = row.get('Название товара в Kaspi Магазине'),
            material_desc_own = row.get('Название в системе продавца'),
            address = row.get('Адрес самовывоза/доставки'),
            status = row.get('Статус'),
            cancellation_reason = row.get('Отменен покупателем (Другое)'),
            payment_method = row.get('Способ оплаты'),
            shipment_method = row.get('Способ доставки'),
            volume = row.get('Количество'),
            value = row.get('Сумма'),
            ship_price_cust = row.get('Стоимость доставки для покупателя'),
            ship_price_store = row.get('Стоимость доставки для продавца'),
            ship_compensation = row.get('Компенсация за доставку')
        ))
        cache.set(f'kaspi_sales_file_progress_{request.session.session_key}', int(index / total_rows * 100), 300)
    cache.set(f'kaspi_sales_file_active_{request.session.session_key}', 0, 300)
    cache.set(f'kaspi_sales_file_progress_{request.session.session_key}', 0, 300)
    return result

def get_progress(request):
    return JsonResponse({'kaspi_sales_file_progress': cache.get(f'kaspi_sales_file_progress_{request.session.session_key}', 0),
                         'kaspi_sales_file_active': cache.get(f'kaspi_sales_file_active_{request.session.session_key}', 0)})

def kaspi_page(request):
    cache.set(f'kaspi_sales_file_active_{request.session.session_key}', 1, 300)
    if 'kaspi_pivot_sku_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('kaspi_pivot_sku_suo', 'on' if request.GET.get('kaspi_pivot_sku_suo') == 'on' else 'off', max_age = 86400)
        return response
    kaspi_pivot_sku_suo = request.COOKIES.get('kaspi_pivot_sku_suo', 'on') == 'on'

    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'sales':
                    upload_file(process_sales_file(form.cleaned_data['file'], request), KASPI_TMP_Sale, '[17_KASPI].[KASPI_PROC_MERGE_Sales]', big=True)
                    return JsonResponse({'status': 'success','redirect_url': reverse('kaspi_page')})
                case _:
                    pass
        else:
            pass
    return render(request, "export_service/kaspi_page.html", context={})