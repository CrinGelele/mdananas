from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page),
    path('ref_sku/', views.ref_sku),
    path('cu/<int:cu_id>/', views.cu_page, name='show_cu'),
    path('cu/create/', views.cu_creation_page, name='cu_create'),
    path('cu/create/save/', views.cu_creation_page_save, name='cu_create_save'),
    path('cu/<int:cu_id>/save/', views.cu_page_save, name='save_cu'),
    path('cu/<int:cu_id>/save-dimensions/', views.cu_page_save_dimensions, name='save_cu_dimensions'),
    path('cu/<int:cu_id>/save-supplier/', views.cu_page_save_supplier, name='save_cu_supplier'),
    path('cu/<int:cu_id>/save-customs_info/', views.cu_page_save_customs_info, name='save_cu_customs_info'),
    path('tu/<int:tu_id>/', views.tu_page, name='show_tu'),
    path('tu/create/', views.tu_creation_page, name='tu_create'),
    path('tu/create/save/', views.tu_creation_page_save, name='tu_create_save'),
    path('tu/<int:tu_id>/save/', views.tu_page_save, name='save_tu'),
    path('tu/<int:tu_id>/save-descriptions/', views.tu_page_save_descriptions, name='save_tu_descriptions'),
    path('tu/<int:tu_id>/save-dimensions/', views.tu_page_save_dimensions, name='save_tu_dimensions'),
    path('tu/<int:tu_id>/save-logistics_info/', views.tu_page_save_logistics_info, name='save_tu_logistics_info'),
    path('tu/<int:tu_id>/save-order_info/', views.tu_page_save_order_info, name='save_tu_order_info'),
    path('mix/<int:mix_id>/', views.mix_page, name='show_mix'),
    path('mix/create/', views.mix_creation_page, name='mix_create'),
    path('mix/create/save/', views.mix_creation_page_save, name='mix_create_save'),
    path('mix/<int:mix_id>/save/', views.mix_page_save, name='save_mix'),
    path('mix/<int:mix_id>/save-compositions/', views.mix_page_save_compositions, name='save_mix_compositions')
]
