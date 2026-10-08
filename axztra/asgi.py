"""
Punto de entrada para servidores ASGI (no se usa por ahora, queda disponible).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'axztra.settings')

application = get_asgi_application()
