from django.contrib import admin
from django.urls import path, include
from root_service.views import mdananas_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', mdananas_views.main_page),
    path('root/', include('root_service.urls')),
    path('export/', include('export_service.urls')),
    path('domestic/', include('domestic_service.urls'))
]
