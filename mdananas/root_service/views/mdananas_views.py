from django.http import HttpResponse
from django.shortcuts import render, redirect

def main_page(request):
    return render(request, 'mdananas_page.html', context = {})