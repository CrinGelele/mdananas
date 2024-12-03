from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.main_page),
    path('ref_sku/', views.ref_sku),
    path('cu/<int:cu_id>/', views.cu_page, name='show_cu'),
    path('cu/<int:cu_id>/save/', views.cu_page_save, name='save_cu')
]
