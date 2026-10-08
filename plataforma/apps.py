"""
Configuración de la aplicación plataforma.
"""

from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


# Al iniciar la aplicación conecta las señales.
class PlataformaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plataforma'
    verbose_name = 'Plataforma AXZTRA'

    def ready(self):
        from . import senales

        senales.conectar()


# Reemplaza la administración de Django por la versión protegida de sitio_admin.py.
class AxztraAdminConfig(AdminConfig):
    default_site = 'plataforma.sitio_admin.AxztraAdminSite'
