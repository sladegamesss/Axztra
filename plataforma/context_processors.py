"""
Datos disponibles en todas las plantillas.

Por ejemplo: {{ sitio.correo_contacto }}, {{ avisos.total }} o {{ acceso_panel }}.
"""

from functools import cached_property

from django.conf import settings

from .verificacion import sesion_verificada


# Contador de avisos del cliente (cotizaciones por responder y mensajes sin leer).
class AvisosCliente:
    def __init__(self, usuario):
        self.usuario = usuario

    @cached_property
    def cotizaciones(self):
        from .models import EstadoSolicitud, Solicitud

        return Solicitud.objects.filter(cliente=self.usuario, estado__codigo=EstadoSolicitud.COTIZADA).count()

    @cached_property
    def mensajes(self):
        from .models import MensajeSolicitud

        return MensajeSolicitud.objects.filter(solicitud__cliente=self.usuario, es_equipo=True, leido=False).count()

    @property
    def total(self):
        return self.cotizaciones + self.mensajes


# Agrega la configuración del sitio, los avisos y si el usuario puede entrar al panel.
def datos_empresa(request):
    from .models import ConfiguracionSitio

    usuario = request.user
    contexto = {
        'empresa': settings.AXZTRA,
        'sitio': ConfiguracionSitio.actual(),
        'acceso_panel': usuario.is_authenticated and usuario.is_staff and sesion_verificada(request),
        'botpress_scripts': settings.AXZTRA.get('BOTPRESS_SCRIPTS', []),
    }
    if usuario.is_authenticated:
        contexto['avisos'] = AvisosCliente(usuario)
    return contexto
