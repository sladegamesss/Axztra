"""
Paquete de vistas. Cada archivo agrupa las pantallas de un tipo de usuario:
publico.py (Visitante), cuentas.py, cliente.py (Cliente), panel.py (Administrador) y asistente.py.
Aquí quedan las páginas de error 403, 404 y 500.
"""

import logging

from django.http import HttpResponseServerError
from django.shortcuts import render

logger = logging.getLogger('plataforma')


# Página propia para "acceso denegado".
def error_403(request, exception=None):
    return render(request, 'plataforma/error.html', {
        'codigo': 403,
        'titulo': 'No tienes acceso a esta sección',
        'mensaje': 'Si crees que deberías poder verla, pide acceso a un administrador de la cuenta.',
    }, status=403)


# Página propia para "página no encontrada".
def error_404(request, exception=None):
    return render(request, 'plataforma/error.html', {
        'codigo': 404,
        'titulo': 'No encontramos esta página',
        'mensaje': 'La dirección puede estar mal escrita o la página ya no está disponible.',
    }, status=404)


# Página propia para errores del servidor.
def error_500(request):
    try:
        return render(request, 'plataforma/error.html', {
            'codigo': 500,
            'titulo': 'Ocurrió un error inesperado',
            'mensaje': 'El problema quedó registrado. Intenta nuevamente en unos minutos.',
        }, status=500)
    except Exception:
        logger.exception('No fue posible mostrar la página de error')
        return HttpResponseServerError(
            '<!DOCTYPE html><html lang="es-CL"><head><meta charset="UTF-8"><title>Error - AXZTRA</title></head>'
            '<body><h1>Ocurrió un error inesperado</h1><p>Intenta nuevamente en unos minutos.</p></body></html>'
        )
