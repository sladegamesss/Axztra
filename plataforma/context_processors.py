from django.conf import settings

from .verificacion import sesion_verificada


def datos_empresa(request):
    return {
        'empresa': settings.AXZTRA,
        'acceso_panel': request.user.is_authenticated and request.user.is_staff and sesion_verificada(request),
    }
