"""
Rutas principales del proyecto.

Une la administración de datos de Django, el mapa del sitio, la API (/api/v1/) y las rutas de la aplicación.
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from plataforma.sitemaps import MAPAS

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': MAPAS}, name='django.contrib.sitemaps.views.sitemap'),
    path('api/v1/', include('plataforma.api.urls')),
    path('', include('plataforma.urls')),
]

# Páginas de error propias (plantilla error.html).
handler403 = 'plataforma.views.error_403'
handler404 = 'plataforma.views.error_404'
handler500 = 'plataforma.views.error_500'
