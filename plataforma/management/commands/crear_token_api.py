"""
Comando: python manage.py crear_token_api "Nombre del sistema"

Crea un token para la API (CU22) y lo muestra una sola vez.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from plataforma.models import TokenAPI


class Command(BaseCommand):
    help = 'Genera un token para que un sistema externo consulte la API de integración.'

    def add_arguments(self, parser):
        parser.add_argument('nombre', help='Nombre del sistema que usará el token, por ejemplo "Facturación".')
        parser.add_argument('--usuario', help='Correo del administrador responsable del token.')

    def handle(self, *args, **opciones):
        usuario = None
        if opciones.get('usuario'):
            usuario = get_user_model().objects.filter(email__iexact=opciones['usuario'], is_staff=True).first()
            if usuario is None:
                raise CommandError('No existe un usuario del equipo con ese correo.')
        token, valor = TokenAPI.generar(opciones['nombre'], usuario)
        self.stdout.write(self.style.SUCCESS(f'Token creado para "{token.nombre}".'))
        self.stdout.write('Guárdalo ahora, no se volverá a mostrar:')
        self.stdout.write(f'  {valor}')
        self.stdout.write('Úsalo en la cabecera: Authorization: Token <valor>')
