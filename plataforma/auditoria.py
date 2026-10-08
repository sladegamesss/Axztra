"""
Registro de actividad del equipo (tabla plataforma_registroactividad, Tabla 28).
"""

import ipaddress
import logging

from .seguridad import ip_cliente

logger = logging.getLogger('plataforma.auditoria')


# Guarda la IP solo si tiene un formato válido.
def _ip_valida(request):
    if request is None:
        return None
    try:
        return str(ipaddress.ip_address(ip_cliente(request)))
    except ValueError:
        return None


# Agrega una acción al registro de actividad.
def registrar(request, accion, descripcion, solicitud=None, usuario=None):
    from .models import RegistroActividad

    if usuario is None and request is not None and request.user.is_authenticated:
        usuario = request.user
    try:
        return RegistroActividad.objects.create(
            usuario=usuario,
            accion=accion,
            descripcion=descripcion[:300],
            solicitud=solicitud,
            ip=_ip_valida(request),
        )
    except Exception:
        logger.exception('No se pudo registrar la actividad "%s"', descripcion)
        return None
