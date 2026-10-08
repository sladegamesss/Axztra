"""
Punto de entrada para servidores WSGI en producción (Gunicorn o Waitress).
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axztra.settings')

application = get_wsgi_application()
