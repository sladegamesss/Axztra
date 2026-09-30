import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from ..asistente import AsistenteVirtual
from ..models import MensajeAsistente

LARGO_MAXIMO = 500


def _clave_sesion(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _mensajes_de(request):
    if request.user.is_authenticated:
        return MensajeAsistente.objects.filter(usuario=request.user)
    return MensajeAsistente.objects.filter(sesion=_clave_sesion(request), usuario__isnull=True)


@require_POST
def asistente_mensaje(request):
    try:
        cuerpo = json.loads(request.body.decode('utf-8') or '{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Formato de mensaje no válido.'}, status=400)

    texto = str(cuerpo.get('mensaje', '')).strip()
    if not texto:
        return JsonResponse({'error': 'Escribe un mensaje.'}, status=400)
    texto = texto[:LARGO_MAXIMO]

    sesion = _clave_sesion(request)
    usuario = request.user if request.user.is_authenticated else None
    MensajeAsistente.objects.create(usuario=usuario, sesion=sesion, contenido=texto)
    resultado = AsistenteVirtual(request.user).responder(texto)
    MensajeAsistente.objects.create(
        usuario=usuario,
        sesion=sesion,
        contenido=resultado['respuesta'],
        es_asistente=True,
        intencion=resultado['intencion'],
    )
    return JsonResponse(resultado)


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
