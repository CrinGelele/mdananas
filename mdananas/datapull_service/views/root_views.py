from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
import requests
import pandas as pd
from ..forms.root_forms import *
import dateparser
from numpy import nan

def main_page(request):
    result = []
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            df = pd.read_excel(form.cleaned_data['file'], skiprows=3, header=None)
            last_date = dateparser.parse(df.iloc[0, 2][-10:])
            header = []
            for index, column in enumerate(df.columns):
                header.append({
                    'column_name': column,
                    'first_lvl': df.iloc[2, index],
                    'second_lvl': df.iloc[3, index],
                    'third_lvl': df.iloc[4, index]
                })
            for index, row in df.iterrows():
                if index < 5:
                    continue
                datarow = {
                    'date_year': None,
                    'date_month': None,
                    'date_day': None,
                    'xcode': None,
                    'customer': None,
                    'gsv': None,
                    'nsv': None,
                    'cu': None,
                    'isv': None,
                    'contract_conditions': None,
                    'price_increase_delay': None
                }
                last_measure = None
                for col in header:
                    if col.get('first_lvl') == 'Контрагент':
                        datarow['customer'] = row.get(col.get('column_name'))
                    elif col.get('first_lvl') == 'Артикул':
                        datarow['xcode'] = row.get(col.get('column_name'))
                    elif col.get('first_lvl') == 'Регистратор':
                        reg = row.get(col.get('column_name'))
                        if 'Объект не найден' in reg:
                            datarow['date_year'] = last_date.year
                            datarow['date_month'] = last_date.month
                            datarow['date_day'] = last_date.day
                        else:
                            current_date = dateparser.parse(reg[-19: -9])
                            datarow['date_year'] = current_date.year
                            datarow['date_month'] = current_date.month
                            datarow['date_day'] = current_date.day
                    if col.get('second_lvl') is not nan:
                        match col.get('second_lvl'):
                            case 'Штуки':
                                last_measure = 'cu'
                            case 'GSV':
                                last_measure = 'gsv'
                            case 'ISV':
                                last_measure = 'isv'
                            case 'NSV':
                                last_measure = 'nsv'
                            case 'Contract conditions':
                                last_measure = 'contract_conditions'
                            case 'Price increase delay':
                                last_measure = 'price_increase_delay'
                            case _:
                                last_measure = 'junk'
                    if col.get('third_lvl') == 'Сумма' and last_measure != 'junk':
                        datarow[last_measure] = row.get(col.get('column_name'))
                result.append(datarow)
    return render(request, 'datapull_service/root_page.html', context={})