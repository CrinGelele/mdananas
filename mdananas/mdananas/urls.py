from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('root/', include('root_service.urls')),
    path('export/', include('export_service.urls')),
    path('domestic/', include('domestic_service.urls'))
]
