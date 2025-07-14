from django.urls import path
from .views import dm_views
from .views import av_views

urlpatterns = [
    path('', dm_views.main_page, name='main_page'),
    path('dm/',dm_views.dm_page, name='dm_page'),
    path('dm/get-progress/', dm_views.get_progress, name='get_progress'),
    path('av/', av_views.av_page, name='av_page'),
    path('av/get-progress/', av_views.get_progress, name='get_progress'),
]
