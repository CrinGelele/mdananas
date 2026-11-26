import csv
import logging
import re
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import BadZipFile

from django.contrib import messages
from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, connections, transaction
from django.db.models import Case, Max, Q, When
from django.http import JsonResponse
from django.shortcuts import redirect, render
from openpyxl import load_workbook

from root_service.models.ref_sku_models import CMP, Cu

from ..forms.ge_forms import CuMappingForm, FileUploadForm, MappingForm, SkuRefForm, StoreRefForm
from ..models.ge_models import (
    GE_PIVOT_CompetingSKU, GE_PIVOT_SKU, GE_PIVOT_Store, GE_REF_SKU, GE_REF_Store, GE_RootSKU,
)

logger = logging.getLogger(__name__)


NETWORK_FOLDER = r"\\hru03\Public\BI\40. ERP data for SQL"
CSV_HEADERS = {
    'sales': ('eng', 'date', 'material', 'sales', 'value', 'store_ge'),
    'stock': ('eng', 'material', 'store_ge', 'stock', 'date'),
}
EXCEL_COLUMNS = {
    'sales': ('დასახელება(ინგლისურად)', 'თარიღი', 'საქონელი', 'რაოდენობა', 'თანხა', 'საწყობი'),
    'stock': ('დასახელება(ინგლისურად)', 'საქონელი', 'საწყობი', 'რაოდენობა'),
}
PROCEDURES = {
    'sales': '[dbo].[GE_PROC_MERGE_Sales]',
    'stock': '[dbo].[GE_PROC_MERGE_Stock]',
}


def stock_sheet_date(title, period):
    parts = re.fullmatch(r'(\d{1,2})[,.](\d{1,2})', title.strip())
    if parts:
        day, month = map(int, parts.groups())
        if month == period.month:
            try:
                return date(period.year, month, day).strftime('%d.%m.%Y')
            except ValueError:
                pass
    raise ValueError(f'Проверьте дату листа «{title}» и месяц в имени файла остатков.')


def excel_number(value):
    return format(value, '.15g').replace('.', ',') if isinstance(value, float) else value


def write_excel_csv(file, kind, output, progress_key=None):
    period = None
    if kind == 'stock':
        months = re.findall(r'(?<!\d)(0?[1-9]|1[0-2])\.(\d{4})(?!\d)', Path(file.name).stem)
        if len(months) != 1:
            raise ValueError('Укажите месяц и год в имени файла остатков, например Stock 10.2026.xlsx.')
        month, year = months[0]
        period = date(int(year), int(month), 1)

    try:
        workbook = load_workbook(file, read_only=True, data_only=True, keep_links=False)
    except BadZipFile as error:
        raise ValueError('Не удалось прочитать файл Excel (.xlsx).') from error

    writer = csv.writer(output, delimiter=';')
    try:
        writer.writerow(CSV_HEADERS[kind])
        sheets = workbook.worksheets if kind == 'stock' else [workbook.worksheets[0]]
        total_rows = sum(sheet.max_row or 0 for sheet in sheets)
        rows_read = 0
        for sheet in sheets:
            rows = sheet.values
            header = [str(value).strip() for value in next(rows, ())]
            if kind == 'sales' and 'გენერიული დასახელება(ლათინურად)' in header and 'უნიკალური კოდი' not in header:
                raise ValueError('В выбранном файле продажи конкурентов. Выберите файл с нашими продажами.')
            try:
                columns = [header.index(name) for name in EXCEL_COLUMNS[kind]]
            except ValueError as error:
                raise ValueError(f'На листе «{sheet.title}» нет заголовков отчёта.') from error
            snapshot = stock_sheet_date(sheet.title, period) if kind == 'stock' else None
            has_data = False
            for row in rows:
                rows_read += 1
                if progress_key and total_rows and rows_read % 1000 == 0:
                    cache.set(progress_key, min(99, rows_read * 100 // total_rows), 300)
                values = [row[column] for column in columns]
                if all(value is None for value in values):
                    continue
                # BULK INSERT считает разделителем даже точку с запятой внутри кавычек.
                if any(isinstance(value, str) and re.search(r'[;\r\n]', value) for value in values):
                    raise ValueError(f'На листе «{sheet.title}» в значении есть точка с запятой или перенос строки.')
                if kind == 'stock':
                    eng, material, store, quantity = values
                    writer.writerow((eng, material, store, excel_number(quantity), snapshot))
                else:
                    eng, sale_date, material, quantity, amount, store = values
                    if isinstance(sale_date, date):
                        sale_date = sale_date.strftime('%d.%m.%Y')
                    writer.writerow((eng, sale_date, material, excel_number(quantity), excel_number(amount), store))
                has_data = True
            if not has_data:
                raise ValueError(f'Лист «{sheet.title}» пуст.')
    finally:
        workbook.close()


def upload_ge_file(file, kind, progress_key=None):
    procedure = PROCEDURES[kind]
    if Path(file.name).suffix.lower() != '.xlsx':
        raise ValueError('Выберите файл Excel (.xlsx).')
    output = NamedTemporaryFile(mode='w', dir=NETWORK_FOLDER, prefix='ge_', suffix='.csv',
                               encoding='utf-8-sig', newline='', delete=False)
    path = Path(output.name)
    try:
        with output:
            write_excel_csv(file, kind, output, progress_key)

        if progress_key:
            cache.set(progress_key, 99, 300)
        with transaction.atomic(using='ideal'), connections['ideal'].cursor() as cursor:
            cursor.execute(f"EXEC {procedure} %s", [str(path)])
            while cursor.nextset():
                pass
    finally:
        path.unlink(missing_ok=True)


def get_progress(request):
    upload_id = request.GET.get('upload_id', '')
    return JsonResponse({'upload_progress': cache.get(f'ge_file_progress_{upload_id}', 0)})


def verified_sku_cards(cu_id):
    return GE_REF_SKU.objects.filter(ge_pivot_sku__root_cu_id=cu_id).distinct()


@transaction.atomic(using='ideal')
def save_sku_mapping(pivot_id, root_cu_id, ref_id=None, root_sku_id=None, **fields):
    pivot = GE_PIVOT_SKU.objects.select_for_update().filter(pk=pivot_id).first()
    if pivot is None or (pivot.root_cu_id is not None and pivot.root_cu_id != root_cu_id):
        raise ValueError('Строка уже сопоставлена или отсутствует. Обновите список.')
    if pivot.root_cu_id == root_cu_id:
        return True

    cards = GE_REF_SKU.objects.select_for_update()
    if pivot.ge_sku_id:
        card = cards.get(pk=pivot.ge_sku_id)
    else:
        verified = list(verified_sku_cards(root_cu_id).values_list('pk', flat=True))
        if ref_id is not None:
            if ref_id not in verified:
                raise ValueError('Выберите грузинскую карточку этого CU.')
            card = cards.get(pk=ref_id)
        elif root_sku_id is not None:
            if verified:
                raise ValueError('У этого CU уже есть грузинская карточка. Повторите выбор в таблице.')
            card, _ = cards.get_or_create(root_sku_id=root_sku_id, defaults=fields)
        elif len(verified) == 1:
            card = cards.get(pk=verified[0])
        else:
            return False

    linked = GE_PIVOT_SKU.objects.filter(ge_sku_id=card.pk, root_cu_id__isnull=False)
    if linked.exclude(root_cu_id=root_cu_id).exists():
        raise ValueError('Грузинская карточка уже используется для другого CU. Проверьте выбранный товар.')
    pivot.root_cu_id = root_cu_id
    pivot.ge_sku_id = card.pk
    pivot.save(update_fields=['root_cu', 'ge_sku'])
    return True


@transaction.atomic(using='ideal')
def save_reference(model, ref_id, **fields):
    if ref_id is None:
        model.objects.create(**fields)
        return

    if model == GE_REF_SKU:
        card = model.objects.select_for_update().filter(pk=ref_id).first()
        if (card and card.root_sku_id != fields['root_sku_id']
                and GE_PIVOT_SKU.objects.filter(ge_sku=card).exists()):
            raise ValueError('Эта карточка используется в отчётах. Артикул в ней изменить нельзя.')
    if not model.objects.filter(pk=ref_id).update(**fields):
        raise ValueError('Запись справочника больше не существует.')


def submit_ge_form(request):
    kind = request.POST.get('form_name')
    if kind == 'sku_ref' and request.POST.get('pivot_id'):
        kind = 'sku_map'
    form_class = {
        'sales': FileUploadForm, 'stock': FileUploadForm,
        'sku_map': CuMappingForm,
        'cmp_map': MappingForm,
        'store_map': MappingForm,
        'sku_ref': SkuRefForm, 'store_ref': StoreRefForm,
    }.get(kind)
    error = None
    try:
        if form_class is None:
            raise ValueError('Неизвестное действие.')
        form = form_class(request.POST, request.FILES)
        if not form.is_valid():
            raise ValueError(form.errors.as_text())
        data = form.cleaned_data

        if kind in PROCEDURES:
            upload_id = request.POST.get('ge_upload_id')
            progress_key = f'ge_file_progress_{upload_id}' if upload_id else None
            upload_ge_file(data['file'], kind, progress_key)
            message = 'Продажи загружены.' if kind == 'sales' else 'Остатки загружены.'
        elif kind == 'sku_map':
            if not save_sku_mapping(**data):
                return redirect(f"{request.path}?map_pivot={data['pivot_id']}&root_cu={data['root_cu_id']}")
            message = 'Сопоставление сохранено.'
        elif kind in ('cmp_map', 'store_map'):
            pivot_id = data['pivot_id']
            ref_id = data['ref_id']
            if kind == 'cmp_map':
                updated = GE_PIVOT_CompetingSKU.objects.filter(pk=pivot_id, root_cmp_id=None).update(root_cmp_id=ref_id)
            else:
                updated = GE_PIVOT_Store.objects.filter(pk=pivot_id, ge_store_id=None).update(ge_store_id=ref_id)
            if not updated:
                raise ValueError('Строка уже сопоставлена или отсутствует. Обновите список.')
            message = 'Сопоставление сохранено.'
        else:
            save_reference(GE_REF_SKU if kind == 'sku_ref' else GE_REF_Store, **data)
            message = 'Справочник обновлён.'
    except ValueError as exc:
        error = str(exc)[:400]
    except IntegrityError:
        logger.exception('Ошибка записи GE: %s', kind)
        error = 'IDEAL отклонила запись. Проверьте выбранную позицию и дубли в справочнике.'
    except (DatabaseError, OSError):
        logger.exception('Ошибка GE: %s', kind)
        error = 'Не удалось завершить операцию. Подробности в журнале сервера.'

    ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if error is not None:
        if ajax:
            return JsonResponse({'status': 'error', 'message': error}, status=400)
        messages.error(request, error)
    else:
        messages.success(request, message)
        if ajax:
            return JsonResponse({'status': 'success', 'message': message})
    if kind == 'cmp_map':
        return redirect(f'{request.path}?products=competitors')
    return redirect('ge_page')



def ge_page(request):
    if request.method == 'POST':
        return submit_ge_form(request)

    if 'ge_last_upload' in request.GET:
        response = redirect('ge_page')
        response.set_cookie('ge_last_upload', 'on' if request.GET['ge_last_upload'] == 'on' else 'off', max_age=86400)
        return response

    last_upload = request.COOKIES.get('ge_last_upload', 'on') == 'on'
    sku_refs = GE_REF_SKU.objects.select_related('root_sku').order_by('root_sku__xcode')
    store_refs = GE_REF_Store.objects.order_by('translation')
    sku_id = request.GET.get('edit_sku', '')
    store_id = request.GET.get('edit_store', '')
    skus = GE_PIVOT_SKU.objects.filter(root_cu_id=None).select_related('ge_sku__root_sku').order_by(
        Case(When(ge_sku_id=None, then=0), default=1), 'material')
    root_skus = GE_RootSKU.objects.order_by('xcode')
    cus = Cu.objects.select_related('root_pd').order_by('xcode_cu')
    pending_pivot = pending_cu = None
    pending_cards = []
    if 'map_pivot' in request.GET:
        pivot_id = request.GET.get('map_pivot', '')
        cu_id = request.GET.get('root_cu', '')
        if pivot_id.isdecimal() and cu_id.isdecimal():
            pending_pivot = skus.filter(pk=pivot_id).first()
            pending_cu = cus.filter(pk=cu_id).first()
        if pending_pivot is None or pending_cu is None or pending_pivot.ge_sku_id:
            messages.error(request, 'Товар уже сопоставлен или отсутствует. Обновите список.')
            return redirect('ge_page')
        pending_cards = verified_sku_cards(cu_id).select_related('root_sku').order_by('root_sku__xcode')
        other_cards = GE_PIVOT_SKU.objects.filter(ge_sku_id__isnull=False, root_cu_id__isnull=False).exclude(root_cu_id=cu_id)
        root_skus = root_skus.exclude(pk__in=other_cards.values('ge_sku__root_sku_id'))
    selected_sku_ref = sku_refs.filter(id=sku_id).first() if sku_id.isdecimal() else None
    competitors = request.GET.get('products') == 'competitors'
    latest_period = None
    if competitors:
        skus = (
            GE_PIVOT_CompetingSKU.objects.filter(root_cmp_id=None)
            .select_related('ge_competing_sku')
            .order_by('material')
        )
    elif last_upload:
        periods = GE_PIVOT_SKU.objects.aggregate(sales=Max('last_sales_period'), stock=Max('last_stock_period'))
        latest_period = max((period for period in periods.values() if period is not None), default=None)
        if latest_period is None:
            skus = skus.none()
        else:
            skus = skus.filter(Q(last_sales_period=latest_period) | Q(last_stock_period=latest_period))
    return render(request, 'export_service/ge_page.html', {
        'skus': skus,
        'competitors': competitors,
        'last_upload': last_upload,
        'latest_period': latest_period,
        'cmp_options': CMP.objects.order_by('brand', 'rus_description', 'id'),
        'stores': GE_PIVOT_Store.objects.filter(ge_store_id=None).order_by('store_ge'),
        'sku_refs': sku_refs,
        'ge_root_ids': {ref.root_sku_id for ref in sku_refs} if not competitors else set(),
        'store_refs': store_refs,
        'root_skus': root_skus,
        'cus': cus,
        'pending_pivot': pending_pivot,
        'pending_cu': pending_cu,
        'pending_cards': pending_cards,
        'selected_sku_ref': selected_sku_ref,
        'sku_ref_in_use': selected_sku_ref is not None and GE_PIVOT_SKU.objects.filter(ge_sku=selected_sku_ref).exists(),
        'selected_store_ref': store_refs.filter(id=store_id).first() if store_id.isdecimal() else None,
    })
