from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('plataforma.urls')),
]

handler404 = 'plataforma.views.error_404'
handler500 = 'plataforma.views.error_500'
