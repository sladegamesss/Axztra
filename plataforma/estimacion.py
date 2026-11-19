"""
Estimación referencial (RF05, CU02).

Implementa la fórmula de la sección 3.5 del informe:
Total = B(tipo) + max(0, P - 5) x 30.000 x F + suma(funcionalidades x F) + suma(integraciones x F)
El resultado se muestra como un rango entre el 90% y el 115% del total, redondeado a múltiplos de $10.000.
Los valores de las tablas de abajo son los de la Tabla 11 del informe.
El mismo cálculo se repite en el navegador (static/js/estimador.js) con los datos de configuracion_publica().
"""

from decimal import Decimal

# B: precio base según el tipo de sitio (pesos chilenos, sin IVA).
PRECIO_BASE_POR_TIPO = {
    'landing': 220000,
    'corporativo': 300000,
    'portafolio': 260000,
    'servicios': 340000,
    'tienda': 480000,
}

# F: factor del nivel de diseño. Multiplica páginas extra, funcionalidades e integraciones.
FACTOR_COMPLEJIDAD = {
    'basica': Decimal('1.00'),
    'media': Decimal('1.25'),
    'alta': Decimal('1.50'),
}

# P: páginas incluidas en el precio base; desde la sexta se cobra cada página adicional.
PAGINAS_INCLUIDAS = 5
COSTO_PAGINA_ADICIONAL = 30000
MAXIMO_PAGINAS = 60

# Funcionalidades que el cliente puede marcar en el paso 3 y su valor base.
FUNCIONALIDADES = {
    'formulario': {'nombre': 'Formulario de contacto', 'descripcion': 'Tus clientes te escriben desde el sitio.', 'icono': 'fa-regular fa-envelope', 'precio': 40000},
    'galeria': {'nombre': 'Galería de imágenes', 'descripcion': 'Fotos de productos, trabajos o instalaciones.', 'icono': 'fa-regular fa-images', 'precio': 50000},
    'catalogo': {'nombre': 'Catálogo de productos o servicios', 'descripcion': 'Listado ordenado con fichas y precios.', 'icono': 'fa-solid fa-table-list', 'precio': 120000},
    'blog': {'nombre': 'Blog o noticias', 'descripcion': 'Publica artículos, novedades y promociones.', 'icono': 'fa-regular fa-newspaper', 'precio': 110000},
    'reservas': {'nombre': 'Sistema de reservas', 'descripcion': 'Agenda de horas o reservas en línea.', 'icono': 'fa-regular fa-calendar-check', 'precio': 180000},
    'login': {'nombre': 'Cuentas de usuario', 'descripcion': 'Registro e inicio de sesión para tus clientes.', 'icono': 'fa-solid fa-user-lock', 'precio': 150000},
    'tienda': {'nombre': 'Carrito y checkout', 'descripcion': 'Venta en línea con carro de compras.', 'icono': 'fa-solid fa-cart-shopping', 'precio': 320000},
    'multidioma': {'nombre': 'Sitio en dos idiomas', 'descripcion': 'Contenido en español y un idioma adicional.', 'icono': 'fa-solid fa-language', 'precio': 140000},
    'panel': {'nombre': 'Panel para editar contenido', 'descripcion': 'Actualiza textos e imágenes sin programar.', 'icono': 'fa-solid fa-pen-to-square', 'precio': 160000},
}

# Integraciones con servicios externos y su valor base.
INTEGRACIONES = {
    'whatsapp': {'nombre': 'Botón de WhatsApp', 'icono': 'fa-brands fa-whatsapp', 'precio': 15000},
    'redes': {'nombre': 'Enlaces a redes sociales', 'icono': 'fa-solid fa-share-nodes', 'precio': 15000},
    'mapa': {'nombre': 'Ubicación en Google Maps', 'icono': 'fa-solid fa-location-dot', 'precio': 20000},
    'analitica': {'nombre': 'Google Analytics', 'icono': 'fa-solid fa-chart-simple', 'precio': 35000},
    'pagos': {'nombre': 'Pasarela de pago (Webpay, Mercado Pago)', 'icono': 'fa-regular fa-credit-card', 'precio': 200000},
    'correo': {'nombre': 'Correo masivo o newsletter', 'icono': 'fa-solid fa-paper-plane', 'precio': 60000},
}

# Objetivos del sitio (paso 2). No cambian el precio.
OBJETIVOS = {
    'presencia': 'Tener presencia en internet',
    'clientes': 'Conseguir más clientes',
    'mostrar': 'Mostrar productos o servicios',
    'informar': 'Compartir información o novedades',
    'vender': 'Vender en línea',
    'reservas': 'Recibir reservas o pedidos',
}

# Rubros del negocio (paso 2). El asistente los usa para sugerir funcionalidades.
RUBROS = [
    ('comercio', 'Comercio y retail'),
    ('gastronomia', 'Gastronomía'),
    ('salud', 'Salud y bienestar'),
    ('educacion', 'Educación'),
    ('servicios', 'Servicios profesionales'),
    ('construccion', 'Construcción e inmobiliaria'),
    ('turismo', 'Turismo y hotelería'),
    ('tecnologia', 'Tecnología'),
    ('organizacion', 'Organización sin fines de lucro'),
    ('otro', 'Otro'),
]

# Plazo referencial en semanas según el nivel de diseño.
SEMANAS_POR_COMPLEJIDAD = {
    'basica': (1, 2),
    'media': (3, 5),
    'alta': (5, 8),
}


# Calcula un porcentaje del total y lo redondea a múltiplos de $10.000.
def _redondear_porcentaje(total, porcentaje, paso=10000):
    return (total * porcentaje + 50 * paso) // (100 * paso) * paso


# Aplica la fórmula y devuelve el total, el rango, el plazo en semanas y el desglose.
def calcular_estimacion(tipo_sitio, complejidad, num_paginas, funcionalidades, integraciones):
    factor = FACTOR_COMPLEJIDAD.get(complejidad, FACTOR_COMPLEJIDAD['media'])
    try:
        num_paginas = int(num_paginas or 1)
    except (TypeError, ValueError):
        num_paginas = 1
    num_paginas = max(1, min(num_paginas, MAXIMO_PAGINAS))
    funcionalidades = [clave for clave in dict.fromkeys(funcionalidades or []) if clave in FUNCIONALIDADES]
    integraciones = [clave for clave in dict.fromkeys(integraciones or []) if clave in INTEGRACIONES]
    desglose = []

    precio_base = PRECIO_BASE_POR_TIPO.get(tipo_sitio, PRECIO_BASE_POR_TIPO['corporativo'])
    desglose.append({'concepto': 'Precio base del tipo de sitio', 'monto': precio_base})

    paginas_extra = max(0, num_paginas - PAGINAS_INCLUIDAS)
    if paginas_extra:
        monto = int(paginas_extra * COSTO_PAGINA_ADICIONAL * factor)
        concepto = '1 página adicional' if paginas_extra == 1 else f'{paginas_extra} páginas adicionales'
        desglose.append({'concepto': concepto, 'monto': monto})

    for clave in funcionalidades:
        item = FUNCIONALIDADES[clave]
        desglose.append({'concepto': item['nombre'], 'monto': int(item['precio'] * factor)})

    for clave in integraciones:
        item = INTEGRACIONES[clave]
        desglose.append({'concepto': item['nombre'], 'monto': int(item['precio'] * factor)})

    total = sum(linea['monto'] for linea in desglose)
    semanas_min, semanas_max = SEMANAS_POR_COMPLEJIDAD.get(complejidad, SEMANAS_POR_COMPLEJIDAD['media'])
    if 'tienda' in funcionalidades or 'pagos' in integraciones:
        semanas_min += 1
        semanas_max += 1
    if num_paginas > 15:
        semanas_max += 1

    return {
        'total': total,
        'monto_minimo': _redondear_porcentaje(total, 90),
        'monto_maximo': _redondear_porcentaje(total, 115),
        'factor': factor,
        'desglose': desglose,
        'semanas_minimas': semanas_min,
        'semanas_maximas': semanas_max,
        'dias_habiles_minimos': semanas_min * 5,
        'dias_habiles_maximos': semanas_max * 5,
    }


# Datos que necesita estimador.js para calcular lo mismo en el navegador.
def configuracion_publica():
    return {
        'bases': PRECIO_BASE_POR_TIPO,
        'factores': {clave: float(valor) for clave, valor in FACTOR_COMPLEJIDAD.items()},
        'paginasIncluidas': PAGINAS_INCLUIDAS,
        'costoPagina': COSTO_PAGINA_ADICIONAL,
        'maximoPaginas': MAXIMO_PAGINAS,
        'semanas': {clave: list(valor) for clave, valor in SEMANAS_POR_COMPLEJIDAD.items()},
        'funcionalidades': {clave: {'nombre': item['nombre'], 'precio': item['precio']} for clave, item in FUNCIONALIDADES.items()},
        'integraciones': {clave: {'nombre': item['nombre'], 'precio': item['precio']} for clave, item in INTEGRACIONES.items()},
    }


# Convierte códigos de funcionalidades en sus nombres.
def nombres_funcionalidades(claves):
    return [FUNCIONALIDADES[c]['nombre'] for c in claves or [] if c in FUNCIONALIDADES]


# Convierte códigos de integraciones en sus nombres.
def nombres_integraciones(claves):
    return [INTEGRACIONES[c]['nombre'] for c in claves or [] if c in INTEGRACIONES]


# Convierte códigos de objetivos en sus nombres.
def nombres_objetivos(claves):
    return [OBJETIVOS[c] for c in claves or [] if c in OBJETIVOS]
