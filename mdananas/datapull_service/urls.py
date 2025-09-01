from django.urls import path
from .views import priceva_views, root_views

urlpatterns = [
    path('', priceva_views.main_page, name='main_page'),
    path('root/', root_views.main_page, name='root_main_page'),
]
