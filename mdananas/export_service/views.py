import pandas as pd
import dateparser
from numpy import nan
from django.http import HttpResponse
from django.shortcuts import render
from .models import *
from .forms import *


def main_page(request):
    return HttpResponse("Hello, world!")

def process_sales_file(file):
    df = pd.read_excel(file, header=None)
    matrix = df.values
    for i in range(9, 33):  #df.shape[0] - 1):
        if matrix[i][3] is not nan:
            current_sku = matrix[i][3]
            next_continue_flag = True
            continue
        if next_continue_flag:
            next_continue_flag = False
            continue
        for j in range(6, df.shape[1]):
            date = matrix[4][j - (j + 1) % 7]
            if date != 'Итог':
                dt = dateparser.parse(date, languages=['ru'])
                sale_row = {
                    'date_year': dt.year,
                    'date_month': dt.month,
                    'store_kg': matrix[i][5],
                    'rus_description': current_sku,
                    'measure_name': matrix[6][j],
                    'measure_value': matrix[i][j],
                }
                print(sale_row)
    return 0

def kg_page(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            match form.cleaned_data['form_name']:
                case 'Sales':
                    process_sales_file(form.cleaned_data['file'])
                case 'MamaDetki':
                    pass
                case _:
                    pass
    else:
        form = FileUploadForm()
    return render(request, 'export_service/kg_page.html', context={'form': form})