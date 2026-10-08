"""
Administración de datos de Django protegida con la verificación en dos pasos.
"""

from urllib.parse import urlencode

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

from .verificacion import sesion_verificada


# Sitio de administración que solo permite entrar con la sesión verificada.
class AxztraAdminSite(admin.AdminSite):
    site_header = 'AXZTRA - Administración de datos'
    site_title = 'AXZTRA'
    index_title = 'Tablas del sistema'

    def has_permission(self, request):
        return (
            request.user.is_active
            and request.user.is_staff
            and sesion_verificada(request)
        )

    def login(self, request, extra_context=None):
        destino = request.GET.get('next') or reverse('admin:index')
        return redirect(f"{reverse('login')}?{urlencode({'next': destino})}")
