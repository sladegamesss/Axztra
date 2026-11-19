#!/usr/bin/env python
# Herramienta de línea de comandos de Django: python manage.py <comando> (runserver, migrate, test, etc.).
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axztra.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            'No se pudo importar Django. Verifica que el entorno virtual esté activo '
            'y que las dependencias estén instaladas con: pip install -r requirements.txt'
        ) from exc
    from django.core.exceptions import ImproperlyConfigured
    try:
        execute_from_command_line(sys.argv)
    except ImproperlyConfigured as error:
        # Sin el conector psycopg Django no puede ni arrancar; se explica cómo instalarlo.
        if 'psycopg' in str(error):
            sys.exit('Falta el conector de PostgreSQL (psycopg). Con el entorno virtual activado ejecuta: pip install -r requirements.txt')
        raise


if __name__ == '__main__':
    main()
