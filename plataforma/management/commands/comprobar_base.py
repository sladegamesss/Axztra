"""
Comando: python manage.py comprobar_base

Comprueba que Django pueda conectarse a la base de datos y, si no puede, explica qué revisar.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import OperationalError, connection


class Command(BaseCommand):
    help = 'Comprueba la conexión con la base de datos y explica qué revisar si falla.'

    def handle(self, *args, **opciones):
        try:
            datos = connection.settings_dict
            destino = f"{datos.get('USER') or 'sin usuario'}@{datos.get('HOST') or 'local'}:{datos.get('PORT') or 'sin puerto'}/{datos['NAME']}"
            connection.ensure_connection()
        except OperationalError as error:
            raise CommandError(
                f'No se pudo conectar con {destino}.\n'
                f'Detalle: {str(error).strip()}\n'
                'Revisa lo siguiente:\n'
                '1. PostgreSQL debe estar encendido (en Windows es el servicio "postgresql-x64-NN").\n'
                '2. La base de datos debe existir; en pgAdmin: clic derecho en Databases, Create, Database, y usa el nombre de POSTGRES_DB.\n'
                '3. POSTGRES_USER y POSTGRES_PASSWORD del archivo .env deben ser los que elegiste al instalar PostgreSQL.'
            )
        with connection.cursor() as cursor:
            cursor.execute('SELECT version()' if connection.vendor == 'postgresql' else 'SELECT sqlite_version()')
            version = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f'Conexión correcta con {destino}.'))
        self.stdout.write(str(version))
