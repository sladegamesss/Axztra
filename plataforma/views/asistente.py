"""
Vistas del asistente virtual (CU03 Consultar asistente virtual).

El navegador las llama con fetch desde static/js/app.js. El asistente solo se muestra
en las pantallas para crear una solicitud.
"""

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ..asistente import AsistenteVirtual
from ..models import MensajeAsistente
from ..recomendaciones import sugerir
from ..seguridad import limitar

LARGO_MAXIMO = 500


# Identificador de la conversación, guardado en la sesión.
def _clave_sesion(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


# Mensajes anteriores de la conversación actual.
def _mensajes_de(request):
    if request.user.is_authenticated:
        return MensajeAsistente.objects.filter(usuario=request.user)
    return MensajeAsistente.objects.filter(sesion=_clave_sesion(request), usuario__isnull=True)


# Lee el cuerpo JSON de la petición de forma segura.
def _leer_json(request):
    try:
        datos = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return None
    return datos if isinstance(datos, dict) else None


# Recibe una pregunta, la responde con AsistenteVirtual y guarda ambos mensajes.
@require_POST
@limitar('asistente', 40, 60, como_json=True)
def asistente_mensaje(request):
    datos = _leer_json(request)
    if datos is None:
        return JsonResponse({'error': 'Formato de mensaje no válido.'}, status=400)
    texto = str(datos.get('mensaje', '')).strip()
    if not texto:
        return JsonResponse({'error': 'Escribe un mensaje.'}, status=400)
    texto = texto[:LARGO_MAXIMO]

    sesion = _clave_sesion(request)
    usuario = request.user if request.user.is_authenticated else None
    resultado = AsistenteVirtual(request.user).responder(texto)
    MensajeAsistente.objects.bulk_create([
        MensajeAsistente(usuario=usuario, sesion=sesion, contenido=texto),
        MensajeAsistente(usuario=usuario, sesion=sesion, contenido=resultado['respuesta'], es_asistente=True, intencion=resultado['intencion']),
    ])
    return JsonResponse(resultado)


# Devuelve la conversación para mostrarla al abrir la ventana.
@require_GET
def asistente_historial(request):
    ultimos = list(_mensajes_de(request).order_by('-fecha', '-pk')[:20])
    ultimos.reverse()
    asistente = AsistenteVirtual(request.user)
    return JsonResponse({
        'saludo': asistente.SALUDO,
        'sugerencias': asistente.SUGERENCIAS_INICIALES,
        'mensajes': [{'texto': m.contenido, 'es_asistente': m.es_asistente} for m in ultimos],
    })


# Sugiere funcionalidades según el rubro y la descripción del negocio (paso 3 del formulario).
@login_required
@require_POST
@limitar('sugerencias', 30, 60, como_json=True, por_usuario=True)
def asistente_sugerencias(request):
    datos = _leer_json(request)
    if datos is None:
        return JsonResponse({'error': 'Formato no válido.'}, status=400)
    objetivos = datos.get('objetivos') or []
    if not isinstance(objetivos, list):
        objetivos = []
    resultado = sugerir(
        str(datos.get('descripcion', ''))[:1500],
        str(datos.get('rubro', ''))[:40],
        [str(o)[:30] for o in objetivos[:10]],
    )
    return JsonResponse(resultado)
