from django.urls import path
from .views.dm_views import *
from .views.av_views import *

urlpatterns = [
    path('', main_page, name='main_page'),
    path('dm/', dm_page, name='dm_page'),
    path('dm/get-progress/', get_progress, name='get_progress'),
    path('av/', av_page, name='av_page'),
    path('av/get-progress/', get_progress, name='get_progress'),
]
