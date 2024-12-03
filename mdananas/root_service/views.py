from django.http import HttpResponse
from django.shortcuts import render, redirect
from .models import Supplier, Cu
from .forms import CuForm

def main_page(request):
    return HttpResponse("Hello, world!")

def ref_sku(request):
    queryset = Cu.objects.all()
    return HttpResponse(queryset[0])

def cu_page(request, cu_id):
    cu_object = Cu.objects.get(id=cu_id)
    return render(request, 'root_service/cu_page.html', context = {"cu": cu_object})

def cu_page_save(request, cu_id):
    cu_object = Cu.objects.get(id=cu_id)
    if request.method == 'POST':
        form = CuForm(request.POST, instance=cu_object)
        if form.is_valid():
            form.save()
    return redirect('show_cu', cu_id=cu_id)