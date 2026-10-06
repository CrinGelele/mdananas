from django.shortcuts import render
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Q
import requests
from django.utils import timezone
from datetime import timezone as datetime_timezone
import pytz
import pandas as pd
from datapull_service.models.pricem_models import *
from datapull_service.forms.pricem_forms import *
from django.db import connections

_INTERNAL_BRANDS_CACHE = None

msk_tz = pytz.timezone('Europe/Moscow')
now_msk = timezone.now().astimezone(msk_tz)

def is_internal_brand(brand):
    global _INTERNAL_BRANDS_CACHE

    if _INTERNAL_BRANDS_CACHE is None:
        with connections['ideal'].cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT brand FROM [00_ROOT].[ROOT_REF_SKU_CU] WHERE brand is NOT NULL
                UNION
                SELECT DISTINCT brand FROM [00_ROOT].[ROOT_REF_SKU_MIX] WHERE brand is NOT NULL
            """)
            _INTERNAL_BRANDS_CACHE = {row[0] for row in cursor.fetchall()}

    return brand in _INTERNAL_BRANDS_CACHE
    
def priceva_api_call():
    url = "https://api.priceva.ru/export?f=ei7/2jw/vCTkK1rtbWOfHhrt0AwY1QUa0Nrx7aO7"
    response = requests.post(url, timeout=30)
    if response.status_code == 200:
        data = pd.read_json(response.text)
    else:
        data = None
    return data

def get_cmp_by_ean(ean):
    try:
        cmp = CMP.objects.get(ean = ean)
    except CMP.DoesNotExist:
        cmp = None
    return cmp

def get_tu_by_xcode(xcode_tu):
    try:
        tu = Tu.objects.get(xcode_tu = xcode_tu)
    except Tu.DoesNotExist:
        tu = None
    return tu

def get_mix_by_xcode(xcode_mix):
    try:
        mix = Mix.objects.get(xcode_mix = xcode_mix)
    except Mix.DoesNotExist:
        mix = None
    return mix

def nullify_empty_string(string):
    if string == '':
        return None
    return string

class IntMonitoringObject():
    tmp_id = None
    real_id = None
    object = None


def process_priceva_data():
    current_date = now_msk.date()
    current_time = int(now_msk.hour)
    data = priceva_api_call()
    print('successful json read', data.head)
    if data is not None:
        for index, row in data.iterrows():
            print(index)
            int_monitoring_flag = is_internal_brand(row.get('brand_name'))
            if int_monitoring_flag:
                monitoring_object = PRICEM_DATA_INT_Monitoring.objects.get_or_create (
                    client_code = row.get('client_code'),
                    root_tu = get_tu_by_xcode(row.get('article')),
                    root_mix = get_mix_by_xcode(row.get('article')),
                )[0]
            else:
                monitoring_object = PRICEM_DATA_EXT_Monitoring.objects.get_or_create (
                    client_code = row.get('client_code'),
                    material = row.get('article'),
                    pricem_description = row.get('name'),
                    category = row.get('category_name'),
                    brand = row.get('brand_name'),
                    root_cmp = get_cmp_by_ean(row.get('article')),
                )[0]
            tags = row.get('tags')
            if isinstance(tags, (list)):
                for tag in tags:
                    tag_object = PRICEM_REF_Tags.objects.get_or_create(tag = tag)[0]
                    PRICEM_LINK_Tags.objects.get_or_create (
                        pricem_int_monitoring = monitoring_object if int_monitoring_flag else None,
                        pricem_ext_monitoring = None if int_monitoring_flag else monitoring_object,
                        pricem_tag = tag_object
                    )
            sources = row.get('sources')
            if isinstance(sources, (list)):
                for source in sources:
                    source_object = PRICEM_DATA_Monitoring_Sources.objects.get_or_create (
                        pricem_int_monitoring = monitoring_object if int_monitoring_flag else None,
                        pricem_ext_monitoring = None if int_monitoring_flag else monitoring_object,
                        url = source.get('url'),
                        root_pivot_customer = ROOT_PIVOT_Customer.objects.get_or_create (
                            erp_name = source.get('company_name'), shipped_to = source.get('company_name')
                        )[0],
                        region = source.get('region_name'),
                        status = int(source.get('status', 0)),
                        sale_option = nullify_empty_string(source.get('option')),
                        formula = nullify_empty_string(source.get('formula')),
                    )[0]
                    if source.get('offers') is None:
                        if nullify_empty_string(source.get('last_check_date')):
                            offer_object = PRICEM_DATA_Source_Offers.objects.get_or_create (
                                upload_date = current_date,
                                upload_time = current_time,
                                pricem_source = source_object,
                                currency = source.get('currency'),
                                last_check_date = timezone.datetime.fromtimestamp(int(source.get('last_check_date')), tz=datetime_timezone.utc),
                                relevance_status = source.get('relevance_status'),
                                in_stock = source.get('in_stock'),
                                price = source.get('price'),
                                discount = source.get('discount'),
                                original_currency = source.get('original_currency'),
                                original_price = source.get('original_price'),
                                offer = source.get('offer')
                            )[0]
                            print(offer_object.upload_date, offer_object.upload_time)
                    else:
                        for offer in source.get('offers'):
                            offer_object = PRICEM_DATA_Source_Offers.objects.get_or_create (
                                pricem_source = source_object,
                                currency = offer.get('currency'),
                                last_check_date = timezone.datetime.fromtimestamp(int(offer.get('last_check_date')), tz=datetime_timezone.utc),
                                relevance_status = offer.get('relevance_status'),
                                in_stock = offer.get('in_stock'),
                                price = offer.get('price'),
                                discount = offer.get('discount'),
                                original_currency = offer.get('original_currency'),
                                original_price = offer.get('original_price'),
                                offer = offer.get('offer'),
                                upload_date = current_date,
                                upload_time = current_time
                            )[0]
                    additional_data = source.get('data')
                    if isinstance(additional_data, (list)):
                        for data in additional_data:
                            PRICEM_DATA_Monitoring_Additional_data.objects.get_or_create (
                                pricem_source = source_object,
                                header = data.get('header'),
                                value = data.get('value'),
                            )
    return JsonResponse({'status': '200 OK'}, safe=False)

def main_page(request):
    if 'pricem_ext_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('pricem_ext_suo', 'on' if request.GET.get('pricem_ext_suo') == 'on' else 'off', max_age = 86400)
        return response
    pricem_ext_suo = request.COOKIES.get('pricem_ext_suo', 'on') == 'on'
    if 'pricem_int_suo' in request.GET:
        response = HttpResponseRedirect(request.path)
        response.set_cookie('pricem_int_suo', 'on' if request.GET.get('pricem_int_suo') == 'on' else 'off', max_age = 86400)
        return response
    pricem_int_suo = request.COOKIES.get('pricem_int_suo', 'on') == 'on'
    int_monitorings = PRICEM_DATA_INT_Monitoring.objects.filter(Q(root_mix=None) & Q(root_tu=None)) if pricem_int_suo else PRICEM_DATA_INT_Monitoring.objects.all()
    ext_monitorings = PRICEM_DATA_EXT_Monitoring.objects.filter(root_cmp=None) if pricem_ext_suo else PRICEM_DATA_EXT_Monitoring.objects.all()
    chains = PRICEM_PIVOT_Promoplan_chain.objects.all()
    schedule = TaskSchedule.objects.all()
    logs = PricemLOG.objects.all()
    existing_tu = Tu.objects.all().order_by('xcode_tu')
    existing_mix = Mix.objects.all().order_by('xcode_mix')
    existing_cmp = CMP.objects.all().order_by('ean')
    existing_customers = ROOT_PIVOT_Customer.objects.all()

    if request.method == 'POST':
        form = NewTaskForm(request.POST)
        if form.is_valid():
            task_object, _ = TaskSchedule.objects.get_or_create(time_hour = form.cleaned_data.get('time_hour'),
                                                                time_minute = form.cleaned_data.get('time_minute'),
                                                                is_active = form.cleaned_data.get('is_active', False))
        else:
            form = ActionTaskForm(request.POST)
            if form.is_valid():
                match form.cleaned_data.get('form_name'):
                    case 'delete_task':
                        TaskSchedule.objects.filter(id = form.cleaned_data.get('task_id')).delete()
                    case 'change_task':
                        TaskSchedule.objects.filter(id = form.cleaned_data.get('task_id')).update(is_active = form.cleaned_data.get('is_active', False))
                    case _:
                        pass
            else:
                form = NewChainForm(request.POST)
                if form.is_valid():
                    source_customer = form.cleaned_data.get('source_customer')
                    promoplan_customer = form.cleaned_data.get('promoplan_customer')
                    chain_object, _ = PRICEM_PIVOT_Promoplan_chain.objects.get_or_create(source_root_pivot_customer = ROOT_PIVOT_Customer.objects.get(id = source_customer) if source_customer else None,
                                                                                         offer = form.cleaned_data.get('offer'),
                                                                                         promoplan_root_pivot_customer = ROOT_PIVOT_Customer.objects.get(id = promoplan_customer) if promoplan_customer else None,
                                                                                         additional_seller = form.cleaned_data.get('additional_seller'))
                else:
                    form = ActionChainForm(request.POST)
                    if form.is_valid():
                        match form.cleaned_data.get('form_name'):
                            case 'delete_chain':
                                PRICEM_PIVOT_Promoplan_chain.objects.filter(id = form.cleaned_data.get('chain_id')).delete()
                            case _:
                                pass
                    else:
                        form = UpdateExtMonitoringForm(request.POST)
                        if form.is_valid():
                            PRICEM_DATA_EXT_Monitoring.objects.filter(id = form.cleaned_data.get('ext_monitoring_id')).update(
                                root_cmp = CMP.objects.get(id = form.cleaned_data.get('root_cmp'))
                            )
                        else:
                            form = UpdateIntMonitoringForm(request.POST)
                            if form.is_valid():
                                object = PRICEM_DATA_INT_Monitoring.objects.get(id = form.cleaned_data['int_monitoring_id'])
                                if form.cleaned_data.get('is_mix'):
                                    object.is_mix = True
                                    object.root_cu = None
                                    object.root_mix = Mix.objects.get(id = form.cleaned_data['root_mix']) if form.cleaned_data['root_mix'] else None
                                else:
                                    object.is_mix = False
                                    object.root_mix = None
                                    object.root_tu = Tu.objects.get(id = form.cleaned_data['root_tu']) if form.cleaned_data['root_tu'] else None
                                object.save()
                            else:
                                print(form.errors)
    return render(request, 'datapull_service/pricem_page.html', context={'int_monitorings': int_monitorings, 'existing_tu': existing_tu, 'existing_mix': existing_mix,
                                                                         'ext_monitorings': ext_monitorings, 'existing_cmp': existing_cmp,
                                                                         'pricem_ext_suo': pricem_ext_suo, 'pricem_int_suo': pricem_int_suo,
                                                                         'existing_customers': existing_customers,
                                                                         'chains': chains, 'schedule': schedule, 'logs': logs})