from django import template

register = template.Library()


@register.filter
def clp(valor):
    try:
        numero = int(round(float(valor)))
    except (TypeError, ValueError):
        return '—'
    signo = '-' if numero < 0 else ''
    return f"{signo}${abs(numero):,}".replace(',', '.')


@register.filter
def color_estado(estado):
    return getattr(estado, 'color', 'azul') or 'azul'


@register.filter
def porcentaje(valor, total):
    try:
        total = float(total)
        if total <= 0:
            return 0
        return round(float(valor) * 100 / total)
    except (TypeError, ValueError):
        return 0


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


@register.filter
def obtener(diccionario, clave):
    if isinstance(diccionario, dict):
        return diccionario.get(clave)
    return None


@register.filter
def es_lista(valor):
    return isinstance(valor, (list, tuple))
