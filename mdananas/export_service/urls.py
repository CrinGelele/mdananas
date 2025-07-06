from django.urls import path
from .views import kg_views

urlpatterns = [
    path('', kg_views.main_page, name='main_page'),
    path('kg/', kg_views.kg_page, name='kg_page'),
    path('kg/sales-file-processing-progress/', kg_views.get_upload_progress, name='get-upload-progress'),
    path('kg/save-stores/', kg_views.kg_page_save_stores, name='kg_page_save_stores'),
    path('kg/save-competitors-sku/', kg_views.kg_page_save_competitors_sku, name='kg_page_save_competitors_sku'),
]
