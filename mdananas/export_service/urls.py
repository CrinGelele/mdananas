from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('kg/', views.kg_page, name='kg_page'),
    path('kg/sales-file-processing-progress/', views.get_upload_progress, name='get-upload-progress'),
]
