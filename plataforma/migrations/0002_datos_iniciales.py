from django.db import migrations

ESTADOS = [
    ('recibida', 'Recibida', 'La solicitud fue registrada y está en cola de revisión.', 1, 'azul', False),
    ('en_revision', 'En revisión', 'El equipo está analizando los requerimientos.', 2, 'cian', False),
    ('cotizada', 'Cotizada', 'La cotización formal está disponible para tu respuesta.', 3, 'violeta', False),
    ('aprobada', 'Aprobada', 'La cotización fue aceptada. Coordinaremos el inicio del trabajo.', 4, 'verde', False),
    ('en_desarrollo', 'En desarrollo', 'El equipo está trabajando en el proyecto.', 5, 'amarillo', False),
    ('completada', 'Completada', 'El trabajo fue entregado.', 6, 'verde', True),
    ('rechazada', 'Cotización rechazada', 'La cotización no fue aceptada.', 7, 'gris', True),
    ('cancelada', 'Cancelada', 'La solicitud fue cancelada.', 8, 'rojo', True),
]

CATEGORIAS = [
    ('Desarrollo web', 'Sitios nuevos diseñados y programados desde cero.', 'fa-solid fa-laptop-code', 1),
    ('Mejoras y optimización', 'Rediseño, velocidad, posicionamiento y nuevas funciones para sitios existentes.', 'fa-solid fa-arrow-trend-up', 2),
    ('Soporte técnico', 'Resolución de incidencias, errores y problemas de seguridad.', 'fa-solid fa-headset', 3),
    ('Mantenimiento', 'Cuidado periódico para que el sitio siga seguro, rápido y actualizado.', 'fa-solid fa-gear', 4),
]

SERVICIOS = [
    {
        'nombre': 'Landing page', 'slug': 'landing-page', 'tipo': 'Creacion', 'categoria': 'Desarrollo web',
        'resumen': 'Una página enfocada en presentar tu oferta y captar contactos.',
        'descripcion': 'Página única pensada para campañas, lanzamientos o servicios puntuales. Incluye estructura orientada a la conversión, diseño adaptado a celulares y botón de contacto directo.',
        'incluye': 'Diseño personalizado\nAdaptación a celulares y tablets\nFormulario o botón de contacto\nEnlaces a redes sociales\nPublicación en tu dominio',
        'precio_base': 220000, 'plazo_referencial': '1 a 2 semanas', 'destacado': True,
    },
    {
        'nombre': 'Sitio web corporativo', 'slug': 'sitio-web-corporativo', 'tipo': 'Creacion', 'categoria': 'Desarrollo web',
        'resumen': 'Sitio de varias páginas para presentar tu empresa, equipo y servicios.',
        'descripcion': 'Sitio institucional con secciones de inicio, nosotros, servicios y contacto. Ideal para empresas y profesionales que necesitan una presencia formal y fácil de actualizar.',
        'incluye': 'Hasta 5 páginas\nDiseño a medida de tu marca\nFormulario de contacto\nUbicación en mapa\nOptimización básica para buscadores',
        'precio_base': 300000, 'plazo_referencial': '2 a 4 semanas', 'destacado': True,
    },
    {
        'nombre': 'Tienda online', 'slug': 'tienda-online', 'tipo': 'Creacion', 'categoria': 'Desarrollo web',
        'resumen': 'Vende tus productos en internet con carrito y medios de pago.',
        'descripcion': 'Tienda con catálogo de productos, carro de compras, checkout y conexión con pasarelas de pago nacionales. Incluye capacitación para que administres tus productos y pedidos.',
        'incluye': 'Catálogo de productos\nCarrito y checkout\nIntegración con Webpay o Mercado Pago\nConfiguración de despachos\nCapacitación de uso',
        'precio_base': 480000, 'plazo_referencial': '4 a 6 semanas', 'destacado': True,
    },
    {
        'nombre': 'Sitio con reservas en línea', 'slug': 'sitio-con-reservas', 'tipo': 'Creacion', 'categoria': 'Desarrollo web',
        'resumen': 'Tus clientes agendan horas o reservas directamente desde la web.',
        'descripcion': 'Sitio para negocios de servicios, salud, belleza o gastronomía que necesitan recibir reservas y agendamientos sin intermediarios.',
        'incluye': 'Calendario de reservas\nConfirmación por correo\nBotón de WhatsApp\nDiseño adaptado a celulares',
        'precio_base': 340000, 'plazo_referencial': '3 a 5 semanas', 'destacado': False,
    },
    {
        'nombre': 'Rediseño de sitio existente', 'slug': 'rediseno-de-sitio', 'tipo': 'Mejora', 'categoria': 'Mejoras y optimización',
        'resumen': 'Moderniza el diseño de tu sitio sin partir de cero.',
        'descripcion': 'Renovamos la imagen y la estructura de tu sitio actual para mejorar su apariencia, su lectura en celulares y la experiencia de tus visitantes.',
        'incluye': 'Diagnóstico del sitio actual\nPropuesta de diseño\nAdaptación a celulares\nMigración de contenido existente',
        'precio_base': 180000, 'plazo_referencial': '2 a 3 semanas', 'destacado': True,
    },
    {
        'nombre': 'Optimización de velocidad y SEO', 'slug': 'optimizacion-velocidad-seo', 'tipo': 'Mejora', 'categoria': 'Mejoras y optimización',
        'resumen': 'Un sitio más rápido y mejor posicionado en Google.',
        'descripcion': 'Revisión técnica para reducir tiempos de carga, corregir errores de indexación y mejorar el posicionamiento orgánico de tu sitio.',
        'incluye': 'Auditoría de rendimiento\nOptimización de imágenes y código\nCorrección de etiquetas SEO\nInforme de resultados',
        'precio_base': 120000, 'plazo_referencial': '1 a 2 semanas', 'destacado': False,
    },
    {
        'nombre': 'Soporte técnico por incidencia', 'slug': 'soporte-tecnico', 'tipo': 'Soporte', 'categoria': 'Soporte técnico',
        'resumen': 'Resolvemos errores, caídas y fallas de tu sitio.',
        'descripcion': 'Atención de problemas puntuales: sitio caído, formularios que no envían, errores tras una actualización o funciones que dejaron de responder.',
        'incluye': 'Diagnóstico del problema\nCorrección de la falla\nPruebas de funcionamiento\nInforme de lo realizado',
        'precio_base': 35000, 'plazo_referencial': '24 a 48 horas', 'destacado': True,
    },
    {
        'nombre': 'Recuperación de sitio vulnerado', 'slug': 'recuperacion-sitio-vulnerado', 'tipo': 'Soporte', 'categoria': 'Soporte técnico',
        'resumen': 'Limpieza y protección de sitios con código malicioso.',
        'descripcion': 'Eliminamos código malicioso, restauramos el sitio a un estado seguro y aplicamos medidas para reducir el riesgo de nuevos ataques.',
        'incluye': 'Análisis de archivos y base de datos\nLimpieza de código malicioso\nCambio de credenciales\nRefuerzo de seguridad',
        'precio_base': 90000, 'plazo_referencial': '1 a 3 días', 'destacado': False,
    },
    {
        'nombre': 'Plan de mantenimiento mensual', 'slug': 'mantenimiento-mensual', 'tipo': 'Mantenimiento', 'categoria': 'Mantenimiento',
        'resumen': 'Respaldos, actualizaciones y monitoreo cada mes.',
        'descripcion': 'Cuidamos tu sitio de forma continua para que se mantenga seguro, actualizado y disponible, con un informe mensual de lo realizado.',
        'incluye': 'Respaldo semanal\nActualizaciones de seguridad\nMonitoreo de disponibilidad\nHasta 2 cambios menores de contenido\nInforme mensual',
        'precio_base': 45000, 'plazo_referencial': 'Valor mensual', 'destacado': True,
    },
    {
        'nombre': 'Plan de mantenimiento trimestral', 'slug': 'mantenimiento-trimestral', 'tipo': 'Mantenimiento', 'categoria': 'Mantenimiento',
        'resumen': 'Revisión y actualización completa cada tres meses.',
        'descripcion': 'Alternativa para sitios con pocos cambios: una revisión trimestral completa con respaldo, actualizaciones y verificación de funcionamiento.',
        'incluye': 'Respaldo completo\nActualizaciones de seguridad\nRevisión de formularios y enlaces\nInforme trimestral',
        'precio_base': 110000, 'plazo_referencial': 'Valor trimestral', 'destacado': False,
    },
]


def cargar(apps, schema_editor):
    EstadoSolicitud = apps.get_model('plataforma', 'EstadoSolicitud')
    Categoria = apps.get_model('plataforma', 'Categoria')
    Servicio = apps.get_model('plataforma', 'Servicio')

    for codigo, nombre, descripcion, orden, color, es_final in ESTADOS:
        EstadoSolicitud.objects.update_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'descripcion': descripcion, 'orden': orden, 'color': color, 'es_final': es_final},
        )

    categorias = {}
    for nombre, descripcion, icono, orden in CATEGORIAS:
        categoria, _ = Categoria.objects.update_or_create(
            nombre=nombre,
            defaults={'descripcion': descripcion, 'icono': icono, 'orden': orden, 'activa': True},
        )
        categorias[nombre] = categoria

    for datos in SERVICIOS:
        datos = dict(datos)
        categoria = categorias[datos.pop('categoria')]
        Servicio.objects.update_or_create(slug=datos['slug'], defaults={**datos, 'categoria': categoria, 'activo': True})


def descargar(apps, schema_editor):
    apps.get_model('plataforma', 'Servicio').objects.filter(slug__in=[s['slug'] for s in SERVICIOS]).delete()
    apps.get_model('plataforma', 'Categoria').objects.filter(nombre__in=[c[0] for c in CATEGORIAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0001_inicial'),
    ]

    operations = [
        migrations.RunPython(cargar, descargar),
    ]
