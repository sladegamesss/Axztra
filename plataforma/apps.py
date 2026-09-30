from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class PlataformaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'plataforma'
    verbose_name = 'Plataforma AXZTRA'


class AxztraAdminConfig(AdminConfig):
    default_site = 'plataforma.sitio_admin.AxztraAdminSite'
