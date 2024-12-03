from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.main_page),
    path('ref_sku/', views.ref_sku),
    path('cu/<int:cu_id>/', views.cu_page, name='show_cu'),
    path('cu/<int:cu_id>/save/', views.cu_page_save, name='save_cu'),
    path('cu/<int:cu_id>/save-dimensions/', views.cu_page_save_dimensions, name='save_cu_dimensions'),
    path('tu/<int:tu_id>/', views.tu_page, name='show_tu')
]
