from decimal import ROUND_HALF_UP, Decimal

PRECIO_BASE_POR_TIPO = {
    'landing': 220000,
    'corporativo': 300000,
    'portafolio': 260000,
    'servicios': 340000,
    'tienda': 480000,
}

FACTOR_COMPLEJIDAD = {
    'basica': Decimal('1.00'),
    'media': Decimal('1.25'),
    'alta': Decimal('1.50'),
}

PAGINAS_INCLUIDAS = 5
COSTO_PAGINA_ADICIONAL = 30000
MAXIMO_PAGINAS = 60

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

INTEGRACIONES = {
    'whatsapp': {'nombre': 'Botón de WhatsApp', 'icono': 'fa-brands fa-whatsapp', 'precio': 15000},
    'redes': {'nombre': 'Enlaces a redes sociales', 'icono': 'fa-solid fa-share-nodes', 'precio': 15000},
    'mapa': {'nombre': 'Ubicación en Google Maps', 'icono': 'fa-solid fa-location-dot', 'precio': 20000},
    'analitica': {'nombre': 'Google Analytics', 'icono': 'fa-solid fa-chart-simple', 'precio': 35000},
    'pagos': {'nombre': 'Pasarela de pago (Webpay, Mercado Pago)', 'icono': 'fa-regular fa-credit-card', 'precio': 200000},
    'correo': {'nombre': 'Correo masivo o newsletter', 'icono': 'fa-solid fa-paper-plane', 'precio': 60000},
}

OBJETIVOS = {
    'presencia': 'Tener presencia en internet',
    'clientes': 'Conseguir más clientes',
    'mostrar': 'Mostrar productos o servicios',
    'informar': 'Compartir información o novedades',
    'vender': 'Vender en línea',
    'reservas': 'Recibir reservas o pedidos',
}

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

SEMANAS_POR_COMPLEJIDAD = {
    'basica': (1, 2),
    'media': (3, 5),
    'alta': (5, 8),
}


def _redondear(valor, paso=10000):
    return int((Decimal(valor) / paso).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * paso)


def calcular_estimacion(tipo_sitio, complejidad, num_paginas, funcionalidades, integraciones):
    factor = FACTOR_COMPLEJIDAD.get(complejidad, FACTOR_COMPLEJIDAD['media'])
    num_paginas = max(1, min(int(num_paginas or 1), MAXIMO_PAGINAS))
    desglose = []

    precio_base = PRECIO_BASE_POR_TIPO.get(tipo_sitio, PRECIO_BASE_POR_TIPO['corporativo'])
    desglose.append({'concepto': 'Precio base del tipo de sitio', 'monto': precio_base})

    paginas_extra = max(0, num_paginas - PAGINAS_INCLUIDAS)
    if paginas_extra:
        monto = int(paginas_extra * COSTO_PAGINA_ADICIONAL * factor)
        desglose.append({'concepto': f'{paginas_extra} páginas adicionales', 'monto': monto})

    for clave in funcionalidades or []:
        item = FUNCIONALIDADES.get(clave)
        if item:
            desglose.append({'concepto': item['nombre'], 'monto': int(item['precio'] * factor)})

    for clave in integraciones or []:
        item = INTEGRACIONES.get(clave)
        if item:
            desglose.append({'concepto': item['nombre'], 'monto': int(item['precio'] * factor)})

    total = sum(linea['monto'] for linea in desglose)
    semanas_min, semanas_max = SEMANAS_POR_COMPLEJIDAD.get(complejidad, SEMANAS_POR_COMPLEJIDAD['media'])
    if 'tienda' in (funcionalidades or []) or 'pagos' in (integraciones or []):
        semanas_min += 1
        semanas_max += 1
    if num_paginas > 15:
        semanas_max += 1

    return {
        'total': total,
        'monto_minimo': _redondear(total * Decimal('0.90')),
        'monto_maximo': _redondear(total * Decimal('1.15')),
        'factor': factor,
        'desglose': desglose,
        'semanas_minimas': semanas_min,
        'semanas_maximas': semanas_max,
        'dias_habiles_minimos': semanas_min * 5,
        'dias_habiles_maximos': semanas_max * 5,
    }


def nombres_funcionalidades(claves):
    return [FUNCIONALIDADES[c]['nombre'] for c in claves or [] if c in FUNCIONALIDADES]


def nombres_integraciones(claves):
    return [INTEGRACIONES[c]['nombre'] for c in claves or [] if c in INTEGRACIONES]


def nombres_objetivos(claves):
    return [OBJETIVOS[c] for c in claves or [] if c in OBJETIVOS]
