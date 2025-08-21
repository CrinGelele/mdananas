from django.urls import path
from .views import priceva_views

urlpatterns = [
    path('', priceva_views.main_page, name='main_page'),
]
