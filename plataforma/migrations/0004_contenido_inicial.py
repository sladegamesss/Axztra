from django.conf import settings
from django.db import migrations

PREGUNTAS = [
    (
        '¿La estimación es el precio final?',
        'No. Es un valor orientativo que se calcula con las reglas de AXZTRA a partir de tus respuestas. '
        'El precio final se informa en la cotización formal, después de que el equipo revisa tus requerimientos.',
        'estimacion, precio final, referencial, valor definitivo, formula',
    ),
    (
        '¿Cuánto demora la cotización formal?',
        'El equipo revisa cada solicitud dentro de 1 a 2 días hábiles. Cuando la cotización está lista, '
        'aparece en tu cuenta y te avisamos por correo.',
        'cotizacion, demora, tarda, respuesta, cuando responden, plazo cotizacion',
    ),
    (
        '¿Necesito conocimientos técnicos para pedir un sitio?',
        'No. El formulario usa un lenguaje simple y cada opción explica para qué sirve. '
        'Si tienes dudas mientras lo completas, el asistente te puede orientar.',
        'conocimientos, tecnico, no se programar, dificil, complicado',
    ),
    (
        '¿Cómo sé en qué etapa está mi proyecto?',
        'En "Mis solicitudes" ves el estado actual, el responsable asignado y el historial completo de cada solicitud. '
        'También te avisamos por correo cada vez que el estado cambia.',
        'etapa, estado, avance, seguimiento, responsable, historial',
    ),
    (
        '¿Puedo cambiar o cancelar una solicitud?',
        'Puedes cancelarla mientras esté recibida o en revisión. Para ajustar el alcance, escríbele al equipo '
        'desde la sección de mensajes de la solicitud y adjunta los archivos que necesites.',
        'cancelar, cambiar, modificar, editar solicitud, arrepentirse',
    ),
    (
        '¿Puedo pagar en línea?',
        'Por ahora no. Los medios y las condiciones de pago se acuerdan en la cotización formal. '
        'Los pagos en línea están considerados para una etapa posterior de la plataforma.',
        'pago, pagar, tarjeta, transferencia, webpay, cuotas, factura',
    ),
    (
        '¿Atienden sitios que no desarrollaron ustedes?',
        'Sí. Los servicios de mejora, soporte y mantenimiento están pensados para sitios existentes, '
        'estén hechos en WordPress, Shopify o a medida.',
        'otro proveedor, wordpress, shopify, sitio existente, hecho por otro',
    ),
    (
        '¿Qué pasa después de aceptar la cotización?',
        'El equipo coordina contigo el inicio del trabajo y actualiza el estado de la solicitud a medida que avanza. '
        'Puedes seguir cada etapa y conversar con el responsable desde tu cuenta.',
        'aceptar cotizacion, despues, siguiente paso, inicio, comenzar',
    ),
    (
        '¿Cómo cuidan mis datos?',
        'Usamos tus datos solo para gestionar tus solicitudes. Desde "Mis datos" puedes descargar una copia '
        'de tu información o eliminar tu cuenta. El acceso del equipo al panel está protegido con verificación en dos pasos.',
        'datos, privacidad, seguridad, eliminar cuenta, informacion personal',
    ),
]


def cargar(apps, schema_editor):
    PreguntaFrecuente = apps.get_model('plataforma', 'PreguntaFrecuente')
    ConfiguracionSitio = apps.get_model('plataforma', 'ConfiguracionSitio')

    for orden, (pregunta, respuesta, palabras) in enumerate(PREGUNTAS, start=1):
        PreguntaFrecuente.objects.get_or_create(
            pregunta=pregunta,
            defaults={'respuesta': respuesta, 'palabras_clave': palabras, 'orden': orden, 'activa': True},
        )

    datos = settings.AXZTRA
    ConfiguracionSitio.objects.get_or_create(
        pk=1,
        defaults={
            'correo_contacto': datos.get('CORREO_CONTACTO', 'contacto@axztra.cl'),
            'whatsapp': datos.get('WHATSAPP', '56912345678'),
            'whatsapp_visible': datos.get('WHATSAPP_VISIBLE', '+56 9 1234 5678'),
            'ubicacion': datos.get('UBICACION', 'Hualpén, Región del Biobío, Chile'),
            'horario': datos.get('HORARIO', 'Lunes a viernes, de 9:00 a 18:00 horas'),
        },
    )


def descargar(apps, schema_editor):
    apps.get_model('plataforma', 'PreguntaFrecuente').objects.filter(pregunta__in=[p[0] for p in PREGUNTAS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('plataforma', '0003_ampliacion_plataforma'),
    ]

    operations = [
        migrations.RunPython(cargar, descargar),
    ]
