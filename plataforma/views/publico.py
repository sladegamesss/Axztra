"""
Vistas públicas: se pueden ver sin iniciar sesión (actor Visitante).

Corresponden a la sección "Público" del diagrama de menús (Tabla 31 del informe).
"""

from django.core.cache import cache
from django.db import connection
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from ..estimacion import FUNCIONALIDADES, configuracion_publica
from ..models import Categoria, PreguntaFrecuente, RequerimientoWeb, Servicio
from ..senales import version_catalogo


TIPOS_SITIO_CORTOS = {
    'landing': 'Landing page',
    'corporativo': 'Corporativo',
    'portafolio': 'Portafolio',
    'servicios': 'Con reservas',
    'tienda': 'Tienda online',
}


# Guarda el catálogo en caché; se invalida solo cuando se modifica un servicio (ver senales.py).
def _catalogo_en_cache(nombre, constructor):
    return cache.get_or_set(f'axztra:catalogo:{version_catalogo()}:{nombre}', constructor, 900)


# Portada: estimador referencial (CU02), tipos de servicio, servicios destacados, planes y preguntas frecuentes.
def inicio(request):
    destacados = _catalogo_en_cache(
        'destacados',
        lambda: list(Servicio.objects.filter(activo=True, destacado=True).select_related('categoria')[:6])
        or list(Servicio.objects.filter(activo=True).select_related('categoria')[:6]),
    )
    preguntas = _catalogo_en_cache('preguntas', lambda: list(PreguntaFrecuente.objects.filter(activa=True)))
    return render(request, 'plataforma/inicio.html', {
        'servicios': destacados,
        'preguntas': preguntas,
        'tipos_sitio': [(clave, TIPOS_SITIO_CORTOS.get(clave, nombre)) for clave, nombre in RequerimientoWeb.TIPOS_SITIO],
        'complejidades': RequerimientoWeb.COMPLEJIDADES,
        'funcionalidades_portada': [
            (clave, FUNCIONALIDADES[clave]['nombre'])
            for clave in ('formulario', 'galeria', 'catalogo', 'blog', 'reservas', 'tienda', 'panel')
        ],
        'config_estimacion': configuracion_publica(),
    })


# CU01 Consultar catálogo de servicios, con búsqueda y filtros por tipo y categoría.
def catalogo(request):
    servicios = Servicio.objects.filter(activo=True).select_related('categoria')
    categorias = _catalogo_en_cache('categorias', lambda: list(Categoria.objects.filter(activa=True)))
    categoria_id = request.GET.get('categoria', '')
    tipo = request.GET.get('tipo', '')
    busqueda = request.GET.get('q', '').strip()[:80]

    if categoria_id.isdigit():
        servicios = servicios.filter(categoria_id=int(categoria_id))
    else:
        categoria_id = ''
    if tipo in dict(Servicio.TIPOS):
        servicios = servicios.filter(tipo=tipo)
    else:
        tipo = ''
    if busqueda:
        servicios = servicios.filter(
            Q(nombre__icontains=busqueda) | Q(resumen__icontains=busqueda) | Q(descripcion__icontains=busqueda)
        )

    return render(request, 'plataforma/catalogo.html', {
        'servicios': list(servicios),
        'categorias': categorias,
        'tipos': Servicio.TIPOS,
        'iconos_tipo': Servicio.ICONOS_TIPO,
        'categoria_activa': categoria_id,
        'tipo_activo': tipo,
        'busqueda': busqueda,
        'hay_filtros': bool(categoria_id or tipo or busqueda),
    })


# Ficha de un servicio del catálogo (CU01).
def servicio_detalle(request, slug):
    servicio = get_object_or_404(Servicio.objects.select_related('categoria'), slug=slug, activo=True)
    relacionados = Servicio.objects.filter(activo=True, tipo=servicio.tipo).exclude(pk=servicio.pk).select_related('categoria')[:3]
    return render(request, 'plataforma/servicio_detalle.html', {
        'servicio': servicio,
        'relacionados': relacionados,
    })


# Página Nosotros con el equipo de AXZTRA.
def nosotros(request):
    return render(request, 'plataforma/nosotros.html')


# Términos y condiciones de uso.
def terminos(request):
    return render(request, 'plataforma/legal/terminos.html')


# Política de privacidad (Ley 19.628).
def privacidad(request):
    return render(request, 'plataforma/legal/privacidad.html')


# Indica a los buscadores qué páginas no deben indexar.
@require_GET
@cache_control(max_age=86400, public=True)
def robots_txt(request):
    lineas = [
        'User-agent: *',
        'Disallow: /cuenta/',
        'Disallow: /panel/',
        'Disallow: /solicitudes/',
        'Disallow: /asistente/',
        'Disallow: /api/',
        f"Sitemap: {request.build_absolute_uri(reverse('django.contrib.sitemaps.views.sitemap'))}",
    ]
    return HttpResponse('\n'.join(lineas) + '\n', content_type='text/plain; charset=utf-8')


# Respuesta simple para comprobar que el servidor y la base de datos están funcionando.
@require_GET
def salud(request):
    estado = {'estado': 'ok', 'base_de_datos': 'ok', 'cache': 'ok'}
    codigo = 200
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        estado['base_de_datos'] = 'error'
        codigo = 503
    try:
        cache.set('axztra:salud', 'ok', 10)
        if cache.get('axztra:salud') != 'ok':
            raise ValueError
    except Exception:
        estado['cache'] = 'error'
        codigo = 503
    if codigo != 200:
        estado['estado'] = 'degradado'
    respuesta = JsonResponse(estado, status=codigo)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta
