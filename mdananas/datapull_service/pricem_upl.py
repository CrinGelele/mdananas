from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
from django.utils import timezone
from datetime import timezone as datetime_timezone
import pandas as pd
from datapull_service.models.pricem_models import *
from django.db import connections

_INTERNAL_BRANDS_CACHE = None

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
        data = pd.read_json(response)
    else:
        data = None
    return data

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

def process_pricem():
    url = "https://api.priceva.ru/export?f=ei7/2jw/vCTkK1rtbWOfHhrt0AwY1QUa0Nrx7aO7"
    #data = priceva_api_call()
    data = pd.read_json('C:/GitRepos/mdananas/mdananas/datapull_service/views/data.json')
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
                                pricem_source = source_object,
                                currency = source.get('currency'),
                                last_check_date = timezone.datetime.fromtimestamp(int(source.get('last_check_date')), tz=datetime_timezone.utc),
                                relevance_status = source.get('relevance_status'),
                                in_stock = source.get('in_stock'),
                                price = source.get('price'),
                                discount = source.get('discount'),
                                original_currency = source.get('original_currency'),
                                original_price = source.get('original_price'),
                                offer = source.get('offer'),
                            )[0]
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