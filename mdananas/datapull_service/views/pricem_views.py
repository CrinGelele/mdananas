from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
import pandas as pd


def main_page(request):
    url = "https://api.priceva.ru/export?f=ei7/2jw/vCTkK1rtbWOfHhrt0AwY1QUa0Nrx7aO7"
    #response = requests.post(url, timeout=30)
    if True: #response.status_code == 200:
        data = pd.read_json('C:/GitRepos/mdananas/mdananas/datapull_service/views/data.json')
        for index, row in data.iterrows():
            # базовая инфа
            client_code = row.get('client_code') # нужно для Semper
            material = row.get('article') # нужно для Semper
            pricem_description = row.get('name')
            tags = row.get('tags') # нужно для Semper
            brand = row.get('brand_name')
            category = row.get('category_name')
            sources = row.get('sources')
            #print(row)
            if isinstance(sources, (list)):
                #print(sources)
                for source in sources:
                    #print(source)
                    additional_data = source.get('data')
                    if isinstance(additional_data, (list)):
                        for data in additional_data:
                            print(data)
    return JsonResponse({'status': '200 OK'}, safe=False) #HttpResponse(df.to_csv(index=False, sep=';'))