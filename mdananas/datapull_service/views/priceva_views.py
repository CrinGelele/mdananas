from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
import pandas as pd

def main_page(request):
    url = "https://api.priceva.ru/export?f=ei7/2jw/vCTkK1rtbWOfHhrt0AwY1QUa0Nrx7aO7"
    response = requests.post(url, timeout=30)
    if response.status_code == 200:
        data = response.json()
        for row in data:
            client_code = row.get('client_code')
            material = row.get('article')
            price_description = row.get('name')
            brand = row.get('brand_name')
            category = row.get('category_name')
            sources = row.get('sources')
            for source in sources:
                url = source.get('url')
                company = source.get('company_name')
                region = source.get('region_name')
                status = source.get('status')
                option = source.get('option')
                formula = source.get('formula')
                currency = source.get('currency')
                last_check_date = source.get('last_check_date')
                relevance_status = source.get('relevance_status')
                price = source.get('price')
                in_stock = source.get('in_stock')
                discount = source.get('discount')
                data = source.get('data')
                for data_row in data:
                    pass
    return HttpResponse("bsuhgbsijn") #HttpResponse(df.to_csv(index=False, sep=';'))