"""
Comando: python manage.py limpiar_datos

Borra códigos vencidos, sesiones expiradas y conversaciones antiguas del asistente,
y actualiza las estadísticas de la base de datos. Conviene programarlo una vez al día.
"""

from datetime import timedelta

from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from plataforma.models import CodigoVerificacion, MensajeAsistente, RegistroActividad


class Command(BaseCommand):
    help = 'Elimina datos temporales vencidos: códigos de verificación, sesiones y conversaciones antiguas del asistente.'

    def add_arguments(self, parser):
        parser.add_argument('--dias-asistente', type=int, default=180, help='Antigüedad máxima de las conversaciones del asistente (por defecto 180 días).')
        parser.add_argument('--dias-actividad', type=int, default=0, help='Si es mayor que cero, elimina registros de actividad más antiguos que esa cantidad de días.')

    def handle(self, *args, **opciones):
        ahora = timezone.now()
        codigos, _ = CodigoVerificacion.objects.filter(expira__lt=ahora - timedelta(days=1)).delete()
        sesiones, _ = Session.objects.filter(expire_date__lt=ahora).delete()
        mensajes, _ = MensajeAsistente.objects.filter(fecha__lt=ahora - timedelta(days=opciones['dias_asistente'])).delete()
        self.stdout.write(f'Códigos de verificación eliminados: {codigos}')
        self.stdout.write(f'Sesiones vencidas eliminadas: {sesiones}')
        self.stdout.write(f'Mensajes antiguos del asistente eliminados: {mensajes}')
        if opciones['dias_actividad'] > 0:
            registros, _ = RegistroActividad.objects.filter(fecha__lt=ahora - timedelta(days=opciones['dias_actividad'])).delete()
            self.stdout.write(f'Registros de actividad eliminados: {registros}')
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                cursor.execute('PRAGMA optimize')
            elif connection.vendor == 'postgresql':
                cursor.execute('ANALYZE')
        self.stdout.write('Estadísticas de la base de datos actualizadas.')
        self.stdout.write(self.style.SUCCESS('Limpieza terminada.'))
