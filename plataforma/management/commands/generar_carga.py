"""
Comando: python manage.py generar_carga --clientes 300 --solicitudes 3000

Genera datos sintéticos para pruebas de volumen y rendimiento.
"""

import random
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from plataforma.estimacion import FUNCIONALIDADES, INTEGRACIONES, calcular_estimacion
from plataforma.models import (
    EstadoSolicitud,
    Estimacion,
    HistorialSolicitud,
    PerfilCliente,
    RequerimientoWeb,
    Servicio,
    Solicitud,
)

User = get_user_model()

NOMBRES = ['Ana', 'Benjamín', 'Camila', 'Diego', 'Elena', 'Felipe', 'Gabriela', 'Hugo', 'Isidora', 'Joaquín', 'Karen', 'Luis', 'Martina', 'Nicolás', 'Olivia', 'Pedro', 'Renata', 'Sebastián', 'Trinidad', 'Vicente']
APELLIDOS = ['Araya', 'Bravo', 'Castro', 'Díaz', 'Espinoza', 'Fuentes', 'Gutiérrez', 'Henríquez', 'Jara', 'Lagos', 'Morales', 'Navarro', 'Orellana', 'Parra', 'Quiroz', 'Riquelme', 'Sepúlveda', 'Toro', 'Valenzuela', 'Zúñiga']
RUBROS = ['comercio', 'gastronomia', 'salud', 'educacion', 'servicios', 'construccion', 'turismo', 'tecnologia']
TITULOS = {
    Servicio.TIPO_CREACION: 'Sitio web para {empresa}',
    Servicio.TIPO_MEJORA: 'Rediseño del sitio de {empresa}',
    Servicio.TIPO_SOPORTE: 'Error en el formulario de {empresa}',
    Servicio.TIPO_MANTENIMIENTO: 'Mantenimiento mensual de {empresa}',
}


class Command(BaseCommand):
    help = 'Genera clientes y solicitudes sintéticas para pruebas de volumen y rendimiento.'

    def add_arguments(self, parser):
        parser.add_argument('--clientes', type=int, default=300)
        parser.add_argument('--solicitudes', type=int, default=3000)
        parser.add_argument('--semilla', type=int, default=2026)

    def handle(self, *args, **opciones):
        azar = random.Random(opciones['semilla'])
        corrida = secrets.token_hex(3)
        ahora = timezone.now()
        clave = make_password('Carga2026')
        estados = {estado.codigo: estado for estado in EstadoSolicitud.objects.all()}
        servicios = {}
        for servicio in Servicio.objects.filter(activo=True):
            servicios.setdefault(servicio.tipo, []).append(servicio)
        codigos = list(estados)

        with transaction.atomic():
            usuarios = [
                User(
                    username=f'carga-{corrida}-{i}@ejemplo.cl',
                    email=f'carga-{corrida}-{i}@ejemplo.cl',
                    first_name=azar.choice(NOMBRES),
                    last_name=azar.choice(APELLIDOS),
                    password=clave,
                    date_joined=ahora - timedelta(days=azar.randint(0, 200)),
                )
                for i in range(opciones['clientes'])
            ]
            User.objects.bulk_create(usuarios, batch_size=500)
            usuarios = list(User.objects.filter(username__startswith=f'carga-{corrida}-'))
            PerfilCliente.objects.bulk_create(
                [PerfilCliente(usuario=u, empresa=f'Empresa {u.last_name} {u.pk}', ciudad='Concepción') for u in usuarios],
                batch_size=500,
            )

            nuevas = []
            requerimientos = []
            for i in range(opciones['solicitudes']):
                tipo = azar.choice([t for t, _ in Solicitud.TIPOS])
                cliente = azar.choice(usuarios)
                requerimiento = None
                if tipo == Servicio.TIPO_CREACION:
                    requerimiento = RequerimientoWeb(
                        nombre_negocio=f'Negocio {i}',
                        rubro=azar.choice(RUBROS),
                        descripcion_negocio='Solicitud generada para pruebas de volumen.',
                        tipo_sitio=azar.choice([c for c, _ in RequerimientoWeb.TIPOS_SITIO]),
                        objetivos=['presencia'],
                        num_paginas=azar.randint(1, 20),
                        complejidad=azar.choice(['basica', 'media', 'alta']),
                        funcionalidades=azar.sample(list(FUNCIONALIDADES), azar.randint(0, 4)),
                        integraciones=azar.sample(list(INTEGRACIONES), azar.randint(0, 3)),
                    )
                    requerimientos.append(requerimiento)
                nuevas.append((Solicitud(
                    numero=f'T{corrida}{i}',
                    cliente=cliente,
                    tipo=tipo,
                    servicio=azar.choice(servicios.get(tipo, [None])),
                    titulo=TITULOS[tipo].format(empresa=f'{cliente.last_name} {cliente.pk}'),
                    descripcion='Solicitud generada para pruebas de volumen.',
                    estado=estados[azar.choice(codigos)],
                    prioridad=azar.choice(['baja', 'media', 'media', 'alta', 'urgente']),
                ), requerimiento))

            RequerimientoWeb.objects.bulk_create(requerimientos, batch_size=500)
            for solicitud, requerimiento in nuevas:
                solicitud.requerimiento = requerimiento
            Solicitud.objects.bulk_create([s for s, _ in nuevas], batch_size=500)

            creadas = list(Solicitud.objects.filter(numero__startswith=f'T{corrida}').select_related('requerimiento'))
            historial = []
            estimaciones = []
            for solicitud in creadas:
                fecha = ahora - timedelta(days=azar.randint(0, 180), hours=azar.randint(0, 23))
                solicitud.fecha_solicitud = fecha
                solicitud.fecha_actualizacion = fecha + timedelta(hours=azar.randint(1, 72))
                solicitud.numero = f"AXZ-{timezone.localtime(fecha):%y%m}-{solicitud.pk:04d}"
                historial.append(HistorialSolicitud(solicitud=solicitud, estado_nuevo=solicitud.estado, comentario='Registro generado para pruebas de volumen.'))
                r = solicitud.requerimiento
                if r is not None:
                    resultado = calcular_estimacion(r.tipo_sitio, r.complejidad, r.num_paginas, r.funcionalidades, r.integraciones)
                    estimaciones.append(Estimacion(
                        solicitud=solicitud,
                        total=resultado['total'],
                        monto_minimo=resultado['monto_minimo'],
                        monto_maximo=resultado['monto_maximo'],
                        factor_complejidad=resultado['factor'],
                        desglose=resultado['desglose'],
                        semanas_minimas=resultado['semanas_minimas'],
                        semanas_maximas=resultado['semanas_maximas'],
                    ))
            Solicitud.objects.bulk_update(creadas, ['numero', 'fecha_solicitud', 'fecha_actualizacion'], batch_size=500)
            HistorialSolicitud.objects.bulk_create(historial, batch_size=500)
            Estimacion.objects.bulk_create(estimaciones, batch_size=500)

        self.stdout.write(self.style.SUCCESS(
            f'Se generaron {len(usuarios)} clientes y {len(creadas)} solicitudes de prueba (contraseña de los clientes: Carga2026).'
        ))
