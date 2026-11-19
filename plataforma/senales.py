"""
Señales de Django: código que se ejecuta automáticamente al guardar o borrar registros.
"""

from django.core.cache import cache
from django.db import transaction
from django.db.backends.signals import connection_created
from django.db.models.signals import post_delete, post_save

CLAVE_VERSION_CATALOGO = 'axztra:catalogo:version'


# Número de versión del catálogo, usado para invalidar la caché.
def version_catalogo():
    version = cache.get(CLAVE_VERSION_CATALOGO)
    if version is None:
        version = 1
        cache.set(CLAVE_VERSION_CATALOGO, version, None)
    return version


# Al cambiar servicios, categorías o preguntas, limpia la caché correspondiente.
def invalidar_catalogo(**kwargs):
    try:
        cache.incr(CLAVE_VERSION_CATALOGO)
    except ValueError:
        cache.set(CLAVE_VERSION_CATALOGO, 2, None)


# Al cambiar los estados, limpia su caché.
def invalidar_estados(**kwargs):
    from .models import CLAVE_CACHE_ESTADOS

    cache.delete(CLAVE_CACHE_ESTADOS)


# Al cambiar la configuración del sitio, limpia su caché.
def invalidar_configuracion(**kwargs):
    from .models import CLAVE_CACHE_CONFIGURACION

    cache.delete(CLAVE_CACHE_CONFIGURACION)


# Al borrar un adjunto, borra también su archivo del disco.
def eliminar_archivo_adjunto(sender, instance, **kwargs):
    archivo = instance.archivo
    if archivo and archivo.name:
        transaction.on_commit(lambda: archivo.storage.delete(archivo.name))


# Activa el modo WAL de SQLite para que soporte más usuarios al mismo tiempo.
def configurar_sqlite(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode=WAL;')
            cursor.execute('PRAGMA synchronous=NORMAL;')


# Conecta todas las señales (se llama desde apps.py).
def conectar():
    from .models import Adjunto, Categoria, ConfiguracionSitio, EstadoSolicitud, PreguntaFrecuente, Servicio

    for modelo in (Servicio, Categoria, PreguntaFrecuente):
        post_save.connect(invalidar_catalogo, sender=modelo, dispatch_uid=f'catalogo_guardado_{modelo.__name__}')
        post_delete.connect(invalidar_catalogo, sender=modelo, dispatch_uid=f'catalogo_borrado_{modelo.__name__}')
    post_save.connect(invalidar_estados, sender=EstadoSolicitud, dispatch_uid='estados_guardado')
    post_delete.connect(invalidar_estados, sender=EstadoSolicitud, dispatch_uid='estados_borrado')
    post_delete.connect(invalidar_configuracion, sender=ConfiguracionSitio, dispatch_uid='configuracion_borrado')
    post_delete.connect(eliminar_archivo_adjunto, sender=Adjunto, dispatch_uid='adjunto_borrado')
    connection_created.connect(configurar_sqlite, dispatch_uid='sqlite_wal')
