"""
API REST para sistemas externos (RF12, CU22).

Las respuestas son JSON. Las rutas de solicitudes exigen la cabecera "Authorization: Token <valor>".
Los tokens se crean con: python manage.py crear_token_api "Nombre del sistema"
"""

import hmac
import json
from datetime import datetime
from functools import wraps

from django.core.paginator import EmptyPage, Paginator
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ..estimacion import FUNCIONALIDADES, INTEGRACIONES, calcular_estimacion
from ..models import RequerimientoWeb, Servicio, Solicitud, TokenAPI
from ..seguridad import limitar


# Respuesta de error en JSON con el código HTTP indicado.
def error(mensaje, estado):
    return JsonResponse({'error': mensaje}, status=estado)


# Decorador que valida el token y registra su último uso.
def requiere_token(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        cabecera = request.headers.get('Authorization', '')
        if not cabecera.startswith('Token '):
            return error('Falta la cabecera Authorization: Token <valor>.', 401)
        valor = cabecera[6:].strip()
        calculado = TokenAPI.calcular_hash(valor)
        token = None
        for candidato in TokenAPI.objects.filter(prefijo=valor[:8], activo=True):
            if hmac.compare_digest(candidato.token_hash, calculado):
                token = candidato
                break
        if token is None:
            return error('Token inválido o desactivado.', 401)
        ahora = timezone.now()
        if token.ultimo_uso is None or (ahora - token.ultimo_uso).total_seconds() > 60:
            TokenAPI.objects.filter(pk=token.pk).update(ultimo_uso=ahora)
        request.token_api = token
        return vista(request, *args, **kwargs)

    return envoltura


# Convierte un servicio en diccionario para la respuesta.
def _servicio(servicio, request):
    return {
        'id': servicio.pk,
        'nombre': servicio.nombre,
        'slug': servicio.slug,
        'tipo': servicio.tipo,
        'tipo_nombre': servicio.get_tipo_display(),
        'categoria': servicio.categoria.nombre if servicio.categoria_id else None,
        'resumen': servicio.resumen,
        'precio_desde': servicio.precio_base or None,
        'plazo_referencial': servicio.plazo_referencial,
        'url': request.build_absolute_uri(servicio.get_absolute_url()),
    }


# Datos mínimos de una persona (nombre y correo).
def _persona(usuario):
    if usuario is None:
        return None
    return {'nombre': usuario.get_full_name(), 'email': usuario.email}


# Convierte una solicitud en diccionario, con o sin detalle.
def _solicitud(solicitud, detalle=False):
    datos = {
        'numero': solicitud.numero,
        'titulo': solicitud.titulo,
        'tipo': solicitud.tipo,
        'tipo_nombre': solicitud.get_tipo_display(),
        'estado': {'codigo': solicitud.estado.codigo, 'nombre': solicitud.estado.nombre},
        'prioridad': solicitud.prioridad,
        'cliente': {
            **_persona(solicitud.cliente),
            'empresa': getattr(getattr(solicitud.cliente, 'perfil_cliente', None), 'empresa', ''),
        },
        'responsable': _persona(solicitud.responsable),
        'fecha_solicitud': solicitud.fecha_solicitud.isoformat(),
        'fecha_actualizacion': solicitud.fecha_actualizacion.isoformat(),
    }
    estimacion = getattr(solicitud, 'estimacion', None)
    datos['estimacion'] = None if estimacion is None else {
        'total': estimacion.total,
        'minimo': estimacion.monto_minimo,
        'maximo': estimacion.monto_maximo,
    }
    cotizacion = getattr(solicitud, 'cotizacion', None)
    datos['cotizacion'] = None if cotizacion is None else {
        'version': cotizacion.version,
        'neto': cotizacion.monto,
        'iva': cotizacion.monto_iva,
        'total': cotizacion.total,
        'plazo_dias': cotizacion.plazo_dias,
        'respuesta_cliente': cotizacion.respuesta_cliente or None,
        'fecha_emision': cotizacion.fecha_emision.isoformat(),
    }
    if detalle:
        datos['descripcion'] = solicitud.descripcion
        datos['url_sitio'] = solicitud.url_sitio
        datos['detalles'] = solicitud.detalles
        datos['historial'] = [
            {
                'estado': h.estado_nuevo.nombre,
                'comentario': h.comentario,
                'fecha': h.fecha.isoformat(),
            }
            for h in solicitud.historial.select_related('estado_nuevo')
        ]
    return datos


# GET /api/v1/servicios/: servicios activos (público).
@require_GET
def servicios(request):
    consulta = Servicio.objects.filter(activo=True).select_related('categoria').order_by('tipo', 'nombre')
    tipo = request.GET.get('tipo')
    if tipo:
        consulta = consulta.filter(tipo=tipo)
    return JsonResponse({'resultados': [_servicio(s, request) for s in consulta]})


# POST /api/v1/estimaciones/: calcula una estimación con la misma fórmula del sitio (público, con límite).
@csrf_exempt
@require_POST
@limitar('api-estimacion', 60, 60, como_json=True)
def estimaciones(request):
    try:
        datos = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return error('El cuerpo debe ser JSON válido.', 400)
    if not isinstance(datos, dict):
        return error('El cuerpo debe ser un objeto JSON.', 400)
    tipo_sitio = datos.get('tipo_sitio', 'corporativo')
    complejidad = datos.get('complejidad', 'media')
    if tipo_sitio not in dict(RequerimientoWeb.TIPOS_SITIO):
        return error('tipo_sitio no es válido.', 400)
    if complejidad not in dict(RequerimientoWeb.COMPLEJIDADES):
        return error('complejidad no es válida.', 400)
    funcionalidades = datos.get('funcionalidades') or []
    integraciones = datos.get('integraciones') or []
    if not isinstance(funcionalidades, list) or not isinstance(integraciones, list):
        return error('funcionalidades e integraciones deben ser listas.', 400)
    desconocidas = [c for c in funcionalidades if c not in FUNCIONALIDADES] + [c for c in integraciones if c not in INTEGRACIONES]
    if desconocidas:
        return error(f'Opciones no reconocidas: {", ".join(map(str, desconocidas))}.', 400)
    resultado = calcular_estimacion(tipo_sitio, complejidad, datos.get('num_paginas', 5), funcionalidades, integraciones)
    resultado['factor'] = float(resultado['factor'])
    resultado['moneda'] = 'CLP'
    resultado['referencial'] = True
    return JsonResponse(resultado)


# GET /api/v1/solicitudes/: listado paginado con filtros (requiere token).
@require_GET
@requiere_token
def solicitudes(request):
    consulta = Solicitud.objects.select_related(
        'estado', 'cliente', 'cliente__perfil_cliente', 'responsable', 'estimacion', 'cotizacion'
    ).order_by('-fecha_solicitud')
    if request.GET.get('estado'):
        consulta = consulta.filter(estado__codigo=request.GET['estado'])
    if request.GET.get('tipo'):
        consulta = consulta.filter(tipo=request.GET['tipo'])
    if request.GET.get('desde'):
        try:
            desde = datetime.strptime(request.GET['desde'], '%Y-%m-%d').date()
        except ValueError:
            return error('El parámetro desde debe tener el formato AAAA-MM-DD.', 400)
        consulta = consulta.filter(fecha_actualizacion__date__gte=desde)
    try:
        por_pagina = min(max(int(request.GET.get('por_pagina', 50)), 1), 200)
        numero = max(int(request.GET.get('pagina', 1)), 1)
    except ValueError:
        return error('pagina y por_pagina deben ser números enteros.', 400)
    paginador = Paginator(consulta, por_pagina)
    try:
        pagina = paginador.page(numero)
    except EmptyPage:
        return JsonResponse({'total': paginador.count, 'pagina': numero, 'paginas': paginador.num_pages, 'resultados': []})
    return JsonResponse({
        'total': paginador.count,
        'pagina': numero,
        'paginas': paginador.num_pages,
        'resultados': [_solicitud(s) for s in pagina.object_list],
    })


# GET /api/v1/solicitudes/<numero>/: detalle de una solicitud (requiere token).
@require_GET
@requiere_token
def solicitud(request, numero):
    encontrada = (
        Solicitud.objects.select_related('estado', 'cliente', 'cliente__perfil_cliente', 'responsable', 'estimacion', 'cotizacion')
        .filter(numero=numero)
        .first()
    )
    if encontrada is None:
        return error('No existe una solicitud con ese número.', 404)
    return JsonResponse(_solicitud(encontrada, detalle=True))
