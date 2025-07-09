from django.urls import path
from . import views

urlpatterns = [
    path('', views.main_page, name='main_page'),
    path('dm/', views.dm_page, name='dm_page'),
    path('dm/get-progress/', views.get_progress, name='get_progress'),
]
