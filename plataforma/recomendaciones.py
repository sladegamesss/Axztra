"""
Sugerencias de funcionalidades según el rubro del negocio.

Las usa el botón "Sugerir funcionalidades" del paso 3 del formulario y el asistente virtual.
"""

import re
import unicodedata

from .estimacion import FUNCIONALIDADES, INTEGRACIONES, RUBROS

PERFILES_RUBRO = {
    'gastronomia': {
        'tipo_sitio': 'servicios',
        'funcionalidades': ['catalogo', 'reservas', 'galeria', 'formulario'],
        'integraciones': ['whatsapp', 'mapa', 'redes'],
        'ideas': 'carta digital con precios, reservas de mesa, galería del local, ubicación y pedidos por WhatsApp',
    },
    'comercio': {
        'tipo_sitio': 'tienda',
        'funcionalidades': ['catalogo', 'tienda', 'formulario'],
        'integraciones': ['pagos', 'whatsapp', 'redes'],
        'ideas': 'catálogo de productos con stock, carro de compras, pago con Webpay o Mercado Pago y consultas por WhatsApp',
    },
    'salud': {
        'tipo_sitio': 'servicios',
        'funcionalidades': ['reservas', 'formulario', 'blog'],
        'integraciones': ['whatsapp', 'mapa'],
        'ideas': 'agenda de horas en línea, ficha de cada profesional, convenios y previsiones, y artículos de prevención',
    },
    'educacion': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['blog', 'formulario', 'galeria', 'login'],
        'integraciones': ['redes', 'mapa'],
        'ideas': 'noticias y calendario, proceso de matrícula, galería de actividades y un área privada para apoderados o alumnos',
    },
    'servicios': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['formulario', 'blog'],
        'integraciones': ['whatsapp', 'analitica'],
        'ideas': 'descripción clara de cada servicio, casos de éxito, formulario de cotización y artículos que muestren tu experiencia',
    },
    'construccion': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['galeria', 'catalogo', 'formulario'],
        'integraciones': ['whatsapp', 'mapa'],
        'ideas': 'portafolio de obras con fotos, fichas de proyectos o propiedades y formulario de contacto por proyecto',
    },
    'turismo': {
        'tipo_sitio': 'servicios',
        'funcionalidades': ['reservas', 'galeria', 'multidioma'],
        'integraciones': ['mapa', 'whatsapp', 'pagos'],
        'ideas': 'reservas en línea, galería de habitaciones o panoramas, versión en inglés y ubicación con cómo llegar',
    },
    'tecnologia': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['blog', 'formulario', 'login'],
        'integraciones': ['analitica', 'correo'],
        'ideas': 'página de producto, planes y precios, blog técnico, registro de usuarios y boletín por correo',
    },
    'organizacion': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['blog', 'galeria', 'formulario'],
        'integraciones': ['redes', 'pagos'],
        'ideas': 'noticias de la organización, galería de actividades, formulario para voluntarios y botón de donaciones',
    },
    'otro': {
        'tipo_sitio': 'corporativo',
        'funcionalidades': ['formulario'],
        'integraciones': ['whatsapp'],
        'ideas': 'una presentación clara de lo que haces, formas de contacto visibles y un botón de WhatsApp',
    },
}

PALABRAS_RUBRO = {
    'gastronomia': ['cafeteria', 'cafe', 'restaurante', 'restoran', 'bar', 'pasteleria', 'panaderia', 'comida', 'sushi', 'pizzeria', 'cocina', 'banqueteria', 'food truck', 'heladeria'],
    'comercio': ['tienda de ropa', 'almacen', 'ferreteria', 'boutique', 'ropa', 'minimarket', 'libreria', 'botilleria', 'zapateria', 'jugueteria', 'emporio', 'distribuidora'],
    'salud': ['clinica', 'dentista', 'dental', 'medico', 'kinesiologo', 'kinesiologia', 'psicologo', 'nutricionista', 'centro medico', 'veterinaria', 'farmacia', 'optica', 'podologia'],
    'educacion': ['colegio', 'escuela', 'academia', 'jardin infantil', 'preuniversitario', 'clases particulares', 'instituto', 'capacitacion'],
    'servicios': ['abogado', 'contador', 'contabilidad', 'consultora', 'estudio juridico', 'arquitecto', 'peluqueria', 'barberia', 'estetica', 'spa', 'gimnasio', 'taller mecanico', 'fotografo', 'agencia'],
    'construccion': ['constructora', 'inmobiliaria', 'corredora de propiedades', 'propiedades', 'remodelacion', 'gasfiter', 'electricista', 'carpinteria'],
    'turismo': ['hotel', 'hostal', 'cabanas', 'turismo', 'agencia de viajes', 'tour', 'camping', 'lodge'],
    'tecnologia': ['software', 'startup', 'aplicacion', 'saas', 'tecnologia', 'informatica'],
    'organizacion': ['fundacion', 'ong', 'junta de vecinos', 'corporacion', 'sindicato', 'club deportivo', 'iglesia'],
}

PALABRAS_FUNCIONALIDAD = {
    'reservas': ['reserva', 'reservas', 'reservar', 'agenda', 'agendar', 'horas', 'citas', 'turnos'],
    'tienda': ['vender', 'venta', 'ventas', 'carrito', 'compras', 'comprar', 'despacho', 'ecommerce'],
    'galeria': ['fotos', 'fotografias', 'imagenes', 'galeria', 'portafolio', 'trabajos realizados'],
    'blog': ['noticias', 'articulos', 'blog', 'novedades', 'publicaciones'],
    'catalogo': ['productos', 'carta', 'menu', 'catalogo', 'servicios y precios', 'lista de precios'],
    'login': ['socios', 'usuarios', 'area privada', 'iniciar sesion', 'intranet', 'alumnos', 'apoderados'],
    'multidioma': ['ingles', 'idiomas', 'turistas', 'extranjeros', 'internacional'],
    'panel': ['actualizar yo', 'editar contenido', 'administrar contenido', 'cambiar textos', 'autoadministrable'],
    'formulario': ['contacto', 'cotizaciones', 'consultas', 'formulario'],
}

PALABRAS_INTEGRACION = {
    'whatsapp': ['whatsapp', 'wsp'],
    'redes': ['instagram', 'facebook', 'redes sociales', 'tiktok', 'linkedin'],
    'mapa': ['ubicacion', 'direccion', 'mapa', 'local fisico', 'sucursal', 'como llegar'],
    'pagos': ['webpay', 'mercado pago', 'pagar', 'pagos', 'tarjeta', 'donaciones', 'donacion'],
    'analitica': ['estadisticas', 'visitas', 'analytics', 'metricas'],
    'correo': ['newsletter', 'boletin', 'correo masivo', 'mailing'],
}


# Pasa el texto a minúsculas y sin tildes para comparar.
def normalizar(texto):
    texto = unicodedata.normalize('NFKD', (texto or '').lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9\s]', ' ', texto)).strip()


# Indica si alguna palabra clave aparece en el texto.
def _contiene(texto, frase):
    return re.search(r'(^|\s)' + re.escape(frase) + r'(s|es)?(\s|$)', texto) is not None


# Adivina el rubro a partir de la descripción del negocio.
def detectar_rubro(texto):
    texto = normalizar(texto)
    mejor, puntaje_mejor = None, 0
    for rubro, palabras in PALABRAS_RUBRO.items():
        puntaje = sum(2 if ' ' in palabra else 1 for palabra in palabras if _contiene(texto, palabra))
        if puntaje > puntaje_mejor:
            mejor, puntaje_mejor = rubro, puntaje
    return mejor


# Nombre legible de un rubro.
def nombre_rubro(clave):
    return dict(RUBROS).get(clave, clave)


# Devuelve las funcionalidades e integraciones recomendadas con su motivo.
def sugerir(descripcion='', rubro='', objetivos=None):
    texto = normalizar(descripcion)
    rubro = rubro if rubro in PERFILES_RUBRO else (detectar_rubro(descripcion) or '')
    objetivos = objetivos or []
    funcionalidades = {}
    integraciones = {}

    def agregar(destino, clave, motivo):
        if clave not in destino:
            destino[clave] = motivo

    for clave, palabras in PALABRAS_FUNCIONALIDAD.items():
        for palabra in palabras:
            if _contiene(texto, normalizar(palabra)):
                agregar(funcionalidades, clave, f'Mencionaste "{palabra}" en la descripción.')
                break
    for clave, palabras in PALABRAS_INTEGRACION.items():
        for palabra in palabras:
            if _contiene(texto, normalizar(palabra)):
                agregar(integraciones, clave, f'Mencionaste "{palabra}" en la descripción.')
                break

    if 'vender' in objetivos:
        agregar(funcionalidades, 'tienda', 'Uno de tus objetivos es vender en línea.')
        agregar(integraciones, 'pagos', 'Para cobrar en línea se necesita una pasarela de pago.')
    if 'reservas' in objetivos:
        agregar(funcionalidades, 'reservas', 'Uno de tus objetivos es recibir reservas o pedidos.')
    if 'informar' in objetivos:
        agregar(funcionalidades, 'blog', 'Para compartir novedades conviene una sección de noticias.')
    if 'mostrar' in objetivos:
        agregar(funcionalidades, 'catalogo', 'Para mostrar lo que ofreces conviene un catálogo ordenado.')
    if 'clientes' in objetivos:
        agregar(funcionalidades, 'formulario', 'Un formulario de contacto facilita que te escriban.')
        agregar(integraciones, 'whatsapp', 'El botón de WhatsApp acorta el camino hacia una conversación.')

    perfil = PERFILES_RUBRO.get(rubro)
    if perfil:
        motivo = f'Es habitual en sitios de {nombre_rubro(rubro).lower()}.'
        for clave in perfil['funcionalidades']:
            agregar(funcionalidades, clave, motivo)
        for clave in perfil['integraciones']:
            agregar(integraciones, clave, motivo)

    return {
        'rubro': rubro,
        'tipo_sitio': perfil['tipo_sitio'] if perfil else '',
        'ideas': perfil['ideas'] if perfil else '',
        'funcionalidades': [
            {'clave': clave, 'nombre': FUNCIONALIDADES[clave]['nombre'], 'motivo': motivo}
            for clave, motivo in funcionalidades.items() if clave in FUNCIONALIDADES
        ],
        'integraciones': [
            {'clave': clave, 'nombre': INTEGRACIONES[clave]['nombre'], 'motivo': motivo}
            for clave, motivo in integraciones.items() if clave in INTEGRACIONES
        ],
    }
