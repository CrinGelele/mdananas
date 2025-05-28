from django.http import HttpResponse
from django.shortcuts import render
from .models import *
from .forms import *

def main_page(request):
    return HttpResponse("Hello, world!")

def kg_page(request):
    return HttpResponse("Hello, world!")