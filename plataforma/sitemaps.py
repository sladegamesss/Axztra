"""
Mapa del sitio para buscadores (/sitemap.xml).
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Servicio


# Páginas públicas fijas.
class PaginasSitemap(Sitemap):
    changefreq = 'monthly'

    def items(self):
        return ['inicio', 'catalogo', 'nosotros', 'terminos', 'privacidad']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == 'inicio' else 0.6


# Fichas de los servicios activos.
class ServiciosSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Servicio.objects.filter(activo=True).order_by('pk')

    def lastmod(self, servicio):
        return servicio.fecha_actualizacion


MAPAS = {'paginas': PaginasSitemap, 'servicios': ServiciosSitemap}
