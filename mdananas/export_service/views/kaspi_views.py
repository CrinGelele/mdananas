from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from zipfile import BadZipFile

import pandas as pd
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import DatabaseError, connections, transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from root_service.models.ref_sku_models import Cu, CMP, PivotCMP

from export_service.forms.kaspi_forms import FileUploadForm, PivotSKUForm
from export_service.models.kaspi_models import KASPI_TMP_Sale, KASPI_PIVOT_SKU
from mdananas.upload_tmp_file import upload_file


KASPI_COLUMNS = {
    '№ заказа': 'order_number',
    'Дата поступления заказа': 'receive_dt',
    'Название товара в Kaspi Магазине': 'material_desc_kaspi',
    'Название в системе продавца': 'material_desc_own',
    'Артикул': 'material',
    'Сумма': 'value',
    'Категория': 'category',
    'Адрес самовывоза/доставки': 'address',
    'Дата изменения статуса': 'change_dt',
    'Статус': 'status',
    'Причина отмены': 'cancellation_reason',
    'Способ оплаты': 'payment_method',
    'Способ доставки': 'shipment_method',
    'Курьерская служба': 'courier_service',
    'Количество': 'volume',
    'Стоимость доставки для покупателя': 'ship_price_cust',
    'Стоимость доставки для продавца': 'ship_price_store',
    'Компенсация за доставку': 'ship_compensation',
    'Требуется подписание': 'signature_required',
    'Плановая дата передачи курьеру': 'plan_dt',
    'Фактическая дата комплектации': 'fact_dt',
    'Склад передачи КД': 'shipment_warehouse',
}

DATE_COLUMNS = ('receive_dt', 'change_dt', 'plan_dt', 'fact_dt')
KASPI_CUSTOMER_ID = 96  # kaspi.kz


def parse_date(value):
    value = (value or '').strip()
    if not value:
        return None

    day, _, time = value.partition(' ')
    date_format = '%d.%m.%Y' if '.' in day else '%Y-%m-%d'
    if time:
        return datetime.strptime(value, f'{date_format} %H:%M:%S')
    return datetime.strptime(value, date_format).date()


def read_sales_file(file):
    df = pd.read_excel(file, dtype=str, keep_default_na=False)
    missing = [column for column in KASPI_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f'В файле Kaspi нет колонок: {", ".join(missing)}')

    rows = df[list(KASPI_COLUMNS)].rename(columns=KASPI_COLUMNS).replace('', None)
    result = []
    for row_no, raw in enumerate(rows.to_dict('records'), start=2):
        record = {'source_row_no': row_no, 'raw': raw}
        for column in DATE_COLUMNS:
            try:
                record[column] = parse_date(raw[column])
            except ValueError as error:
                raise ValueError(f'Строка {row_no}: неверная дата в поле {column}.') from error
        result.append(record)
    return result


def number(value, scale):
    if value is None:
        return None
    result = Decimal(value)
    if not result.is_finite() or result != result.quantize(Decimal(1).scaleb(-scale)):
        raise ValueError(f'Некорректная точность числа {value}.')
    return result


def as_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def prepare_rows(records):
    orders, lines, seen = {}, {}, {}
    for record in records:
        raw = record['raw']
        row_no = record['source_row_no']
        order_number = (raw['order_number'] or '').strip()
        material = (raw['material'] or '').strip()
        if not order_number or not material:
            raise ValueError(f'Строка {row_no}: не заполнен номер заказа или артикул.')

        key = order_number, material
        payload = tuple(raw[field] for field in KASPI_COLUMNS.values())
        if key in seen:
            if seen[key] != payload:
                raise ValueError(
                    f'Строка {row_no}: разные позиции для заказа {order_number} '
                    f'и артикула {material}.'
                )
            continue
        seen[key] = payload

        try:
            receive = record['receive_dt']
            change = record['change_dt']
            plan = record['plan_dt']
            fact = record['fact_dt']
            order = {
                'receive_dt': as_datetime(receive),
                'receive_has_time': isinstance(receive, datetime),
                'change_dt': change.date() if isinstance(change, datetime) else change,
                'plan_dt': plan.date() if isinstance(plan, datetime) else plan,
                'fact_dt': as_datetime(fact),
                'fact_has_time': None if fact is None else isinstance(fact, datetime),
                'address': raw['address'],
                'status': raw['status'],
                'cancellation_reason': raw['cancellation_reason'],
                'payment_method': raw['payment_method'],
                'shipment_method': raw['shipment_method'],
                'courier_service': raw['courier_service'],
                'shipment_warehouse': raw['shipment_warehouse'],
                'signature_required': raw['signature_required'],
                'currency': 'KZT',
                'ship_price_cust': number(raw['ship_price_cust'], 2),
                'ship_price_store': number(raw['ship_price_store'], 2),
                'ship_compensation': number(raw['ship_compensation'], 2),
            }
            line = {
                'material_desc_kaspi': raw['material_desc_kaspi'],
                'material_desc_own': raw['material_desc_own'],
                'category': raw['category'],
                'volume': number(raw['volume'], 3),
                'value': number(raw['value'], 2),
            }
        except (ValueError, InvalidOperation) as error:
            raise ValueError(f'Строка {row_no}: {error}') from error

        if order_number in orders and orders[order_number] != order:
            raise ValueError(f'Заказ {order_number}: общие поля различаются между позициями.')
        orders[order_number] = order
        lines[key] = line
    return orders, lines


def process_sales_file(file, request):
    records = read_sales_file(file)
    if not records:
        raise ValueError('В файле Kaspi нет строк заказов.')
    orders, lines = prepare_rows(records)
    result = []
    for index, ((order_number, material), line) in enumerate(lines.items(), 1):
        order = dict(orders[order_number])
        order['receive_dt'] = order['receive_dt'].isoformat()
        order['fact_dt'] = order['fact_dt'].isoformat() if order['fact_dt'] else None
        result.append(KASPI_TMP_Sale(
            **{**line, **order, 'source_key': 'kaspi_kz',
               'order_number': order_number, 'material': material},
        ))
        cache.set(f'kaspi_sales_file_progress_{request.session.session_key}',
                  int(index / len(lines) * 100), 300)
    return result


def save_sku_mapping(pivot_sku_id, root_cu, root_cmp):
    with transaction.atomic(using='ideal'):
        with connections['ideal'].cursor() as cursor:
            cursor.execute(
                'SET ANSI_NULLS ON; SET QUOTED_IDENTIFIER ON; SET ANSI_PADDING ON; '
                'SET ANSI_WARNINGS ON; SET ARITHABORT ON; '
                'SET CONCAT_NULL_YIELDS_NULL ON; SET NUMERIC_ROUNDABORT OFF;'
            )

        sku = KASPI_PIVOT_SKU.objects.using('ideal').get(id=pivot_sku_id, source_key='kaspi_kz')
        sku.root_cu = root_cu
        sku.root_pivot_sku_cmp = None
        sku.mapping_status = 'own' if root_cu else 'pending'

        if root_cmp and not root_cu:
            lookup = {'root_pivot_customer_id': KASPI_CUSTOMER_ID}
            defaults = {'root_cmp': root_cmp}
            if len(sku.material) <= 20:
                lookup['xcode'] = sku.material
                defaults['material'] = sku.material_desc_own or sku.material_desc_kaspi
            else:
                # В ROOT xcode ограничен 20 символами. Полный код сохраняем в material.
                lookup.update(xcode=None, material=sku.material)

            sku.root_pivot_sku_cmp, _ = PivotCMP.objects.using('ideal').update_or_create(
                **lookup, defaults=defaults,
            )
            sku.mapping_status = 'competitor'

        sku.updated_at = timezone.now()
        sku.save(using='ideal', update_fields=[
            'root_cu', 'root_pivot_sku_cmp', 'mapping_status', 'updated_at',
        ])

    return sku.get_mapping_status_display()


def get_progress(request):
    return JsonResponse({
        'kaspi_sales_file_progress': cache.get(f'kaspi_sales_file_progress_{request.session.session_key}', 0),
    })


def kaspi_page(request):
    if request.method == 'POST':
        if 'pivot_sku_id' in request.POST:
            form = PivotSKUForm(request.POST)
            if not form.is_valid():
                return JsonResponse({'status': 'error', 'message': form.errors.as_text()}, status=400)
            try:
                mapping_status = save_sku_mapping(**form.cleaned_data)
            except (ValueError, DatabaseError, KASPI_PIVOT_SKU.DoesNotExist) as error:
                return JsonResponse({'status': 'error', 'message': str(error)}, status=400)
            return JsonResponse({'status': 'success', 'mapping_status': mapping_status})

        form = FileUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            return JsonResponse(
                {'status': 'error', 'message': 'Выберите файл выгрузки Kaspi.'}, status=400,
            )

        progress_key = f'kaspi_sales_file_progress_{request.session.session_key}'
        cache.set(progress_key, 0, 300)
        try:
            records = process_sales_file(form.cleaned_data['file'], request)
            upload_file(records, KASPI_TMP_Sale, '[17_KASPI].[KASPI_PROC_MERGE_Sales]')
        except BadZipFile:
            return JsonResponse(
                {'status': 'error', 'message': 'Не удалось прочитать Excel. Проверьте файл.'}, status=400,
            )
        except (ValueError, OSError, DatabaseError) as error:
            return JsonResponse({'status': 'error', 'message': str(error)}, status=400)

        return JsonResponse({'status': 'success', 'redirect_url': reverse('kaspi_page')})

    unmapped = request.GET.get('unmapped', '1') == '1'
    skus = KASPI_PIVOT_SKU.objects.using('ideal').select_related('root_pivot_sku_cmp').filter(source_key='kaspi_kz')
    if unmapped:
        skus = skus.filter(mapping_status='pending')
    page = Paginator(skus.order_by('id'), 50).get_page(request.GET.get('page'))

    return render(request, 'export_service/kaspi_page.html', {
        'unmapped': unmapped,
        'page': page,
        'existing_cu': Cu.objects.using('ideal').all().order_by('xcode_cu'),
        'existing_cmp': CMP.objects.using('ideal').all().order_by('brand', 'rus_description'),
    })
