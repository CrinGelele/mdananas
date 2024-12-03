from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Supplier, Cu, CuDimensions
from .forms import CuForm, CuDimensionsForm

def main_page(request):
    return HttpResponse("Hello, world!")

def ref_sku(request):
    queryset = Cu.objects.all()
    return HttpResponse(queryset[0])

def cu_page(request, cu_id):
    cu_object = Cu.objects.get(id=cu_id)
    cu_dimensions, created_cu_dimensions = CuDimensions.objects.get_or_create(root_cu=cu_object)
    return render(request, 'root_service/cu_page.html', context = {"cu": cu_object, "dimensions": created_cu_dimensions if created_cu_dimensions else cu_dimensions})

def cu_page_save(request, cu_id):
    cu_object = Cu.objects.get(id=cu_id)
    if request.method == 'POST':
        form = CuForm(request.POST, instance=cu_object)
        if form.is_valid():
            form.save()
    return redirect('show_cu', cu_id=cu_id)

def cu_page_save_dimensions(request, cu_id):
    cu_object = Cu.objects.get(id=cu_id)
    cu_dimensions, created_cu_dimensions = CuDimensions.objects.get_or_create(root_cu=cu_object)
    if request.method == 'POST':
        form = CuDimensionsForm(request.POST, instance=created_cu_dimensions if created_cu_dimensions else cu_dimensions)
        if form.is_valid():
            form.save()
        else:
            print(form.errors)
    return redirect('show_cu', cu_id=cu_id)

def tu_page(request, tu_id):
    pass