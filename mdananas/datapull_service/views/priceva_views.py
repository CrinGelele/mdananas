from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
import pandas as pd

def main_page(request):
    headers = {'Apikey': 'PDLYzG9wsEjdjx4wrA4DhG7PPZpNkyDd'}
    url = "https://api.priceva.ru/export?f=ei7/2jw/vCTkK1rtbWOfHhrt0AwY1QUa0Nrx7aO7"
    response = requests.post(url, headers=headers, timeout=30)
    if response.status_code == 200:
        data = response.json()
        print(data)
        #df = pd.DataFrame(data.get('result').get('objects'))
    return HttpResponse("bsuhgbsijn") #HttpResponse(df.to_csv(index=False, sep=';'))