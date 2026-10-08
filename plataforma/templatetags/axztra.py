"""
Filtros propios para las plantillas. Se cargan con {% load axztra %}.
"""

from django import template
from django.utils import timezone

register = template.Library()


# Formatea un monto como pesos chilenos: 350000 -> $350.000.
@register.filter
def clp(valor):
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        return '-'
    signo = '-' if numero < 0 else ''
    return f"{signo}${abs(numero):,}".replace(',', '.')


# Calcula un porcentaje para las barras del panel.
@register.filter
def porcentaje(valor, total):
    try:
        total = float(total)
        if total <= 0:
            return 0
        return round(float(valor) * 100 / total)
    except (TypeError, ValueError):
        return 0


# Obtiene un valor de un diccionario dentro de la plantilla.
@register.filter
def obtener(diccionario, clave):
    if isinstance(diccionario, dict):
        return diccionario.get(clave)
    return None


# Indica si un valor es una lista.
@register.filter
def es_lista(valor):
    return isinstance(valor, (list, tuple))


# Iniciales de un nombre para los avatares.
@register.filter
def iniciales(usuario):
    if not usuario:
        return ''
    nombre = (getattr(usuario, 'get_full_name', lambda: '')() or getattr(usuario, 'email', '') or '').strip()
    partes = [p for p in nombre.replace('@', ' ').split() if p]
    if not partes:
        return '?'
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


# Tamaño de archivo legible (KB o MB).
@register.filter
def peso_archivo(valor):
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        return ''
    if valor >= 1024 * 1024:
        return f'{valor / (1024 * 1024):.1f} MB'.replace('.', ',')
    if valor >= 1024:
        return f'{round(valor / 1024)} KB'
    return f'{valor} B'


# Tiempo transcurrido en texto ("hace 2 horas").
@register.filter
def hace(fecha):
    if not fecha:
        return ''
    diferencia = timezone.now() - fecha
    segundos = int(diferencia.total_seconds())
    if segundos < 60:
        return 'hace un momento'
    minutos = segundos // 60
    if minutos < 60:
        return f'hace {minutos} min'
    horas = minutos // 60
    if horas < 24:
        return f'hace {horas} h'
    dias = horas // 24
    if dias == 1:
        return 'ayer'
    if dias < 30:
        return f'hace {dias} días'
    return timezone.localtime(fecha).strftime('%d-%m-%Y')


# Mantiene los filtros actuales al cambiar de página.
@register.simple_tag(takes_context=True)
def url_con_parametros(context, **kwargs):
    parametros = context['request'].GET.copy()
    for clave, valor in kwargs.items():
        if valor in (None, ''):
            parametros.pop(clave, None)
        else:
            parametros[clave] = valor
    codificado = parametros.urlencode()
    return f'?{codificado}' if codificado else '?'
