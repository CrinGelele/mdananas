from django.urls import path
from .views import pricem_views, root_views

urlpatterns = [
    path('root/', root_views.main_page, name='root_main_page'),
    path('root/get-progress/', root_views.get_progress, name='get_progress'),
    path('pricem/', pricem_views.main_page, name='pricem_main_page'),
]
