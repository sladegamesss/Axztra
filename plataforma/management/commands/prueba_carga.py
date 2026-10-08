"""
Comando: python manage.py prueba_carga --usuarios 300

Mide los tiempos de respuesta con muchos usuarios simultáneos (RNF07). Requiere un servidor en ejecución.
"""

import json
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError

from plataforma.models import Servicio

LIMITE_CARGA_SEGUNDOS = 2.0
LIMITE_CONCURRENCIA_SEGUNDOS = 3.0


def percentil(valores, p):
    if not valores:
        return 0.0
    ordenados = sorted(valores)
    indice = min(len(ordenados) - 1, max(0, round(p / 100 * len(ordenados)) - 1))
    return ordenados[indice]


class Command(BaseCommand):
    help = 'Mide tiempos de respuesta con muchos usuarios simultáneos contra un servidor en ejecución.'

    def add_arguments(self, parser):
        parser.add_argument('--url', default='http://127.0.0.1:8000', help='Dirección del servidor a probar.')
        parser.add_argument('--usuarios', type=int, default=300, help='Usuarios simultáneos (por defecto 300).')
        parser.add_argument('--peticiones', type=int, default=5, help='Páginas que visita cada usuario (por defecto 5).')
        parser.add_argument('--tiempo-maximo', type=float, default=30.0, help='Segundos de espera máxima por petición.')

    def handle(self, *args, **opciones):
        base = opciones['url'].rstrip('/')
        slugs = list(Servicio.objects.filter(activo=True).values_list('slug', flat=True)[:6]) or ['landing-page']
        rutas = ['/', '/servicios/', '/nosotros/', '/api/v1/servicios/'] + [f'/servicios/{slug}/' for slug in slugs]
        try:
            with urlopen(f'{base}/salud/', timeout=10) as respuesta:
                json.loads(respuesta.read().decode('utf-8'))
        except (URLError, HTTPError, ValueError) as error:
            raise CommandError(f'No se pudo contactar el servidor en {base}. Inícialo con "python manage.py runserver" antes de la prueba. Detalle: {error}')

        tiempos = {}
        errores = []
        bloqueo = threading.Lock()
        inicio_barrera = threading.Barrier(opciones['usuarios'])

        def usuario(numero):
            try:
                inicio_barrera.wait(timeout=60)
            except threading.BrokenBarrierError:
                pass
            for paso in range(opciones['peticiones']):
                ruta = rutas[(numero + paso) % len(rutas)]
                peticion = Request(f'{base}{ruta}', headers={'User-Agent': 'axztra-prueba-carga', 'Accept-Encoding': 'identity'})
                inicio = time.perf_counter()
                try:
                    with urlopen(peticion, timeout=opciones['tiempo_maximo']) as respuesta:
                        respuesta.read()
                        codigo = respuesta.status
                except HTTPError as error:
                    codigo = error.code
                except (URLError, TimeoutError, ConnectionError, OSError) as error:
                    codigo = str(error)
                duracion = time.perf_counter() - inicio
                with bloqueo:
                    tiempos.setdefault(ruta, []).append(duracion)
                    if codigo != 200:
                        errores.append((ruta, codigo))

        self.stdout.write(f"Probando {base} con {opciones['usuarios']} usuarios simultáneos y {opciones['peticiones']} páginas por usuario...")
        comienzo = time.perf_counter()
        with ThreadPoolExecutor(max_workers=opciones['usuarios']) as ejecutor:
            list(ejecutor.map(usuario, range(opciones['usuarios'])))
        total_segundos = time.perf_counter() - comienzo

        todos = [t for lista in tiempos.values() for t in lista]
        self.stdout.write('')
        self.stdout.write(f'{"Ruta":<42}{"Peticiones":>11}{"Mediana":>10}{"P95":>10}{"Máximo":>10}')
        for ruta in rutas:
            lista = tiempos.get(ruta, [])
            if lista:
                self.stdout.write(f'{ruta:<42}{len(lista):>11}{statistics.median(lista):>9.2f}s{percentil(lista, 95):>9.2f}s{max(lista):>9.2f}s')
        self.stdout.write('')
        p95 = percentil(todos, 95)
        self.stdout.write(f'Total: {len(todos)} peticiones en {total_segundos:.1f} s ({len(todos) / total_segundos:.1f} por segundo)')
        self.stdout.write(f'Mediana: {statistics.median(todos):.2f} s   P95: {p95:.2f} s   P99: {percentil(todos, 99):.2f} s   Máximo: {max(todos):.2f} s')
        self.stdout.write(f'Errores: {len(errores)}')
        for ruta, codigo in errores[:10]:
            self.stdout.write(f'  {ruta}: {codigo}')
        cumple = p95 <= LIMITE_CONCURRENCIA_SEGUNDOS and not errores
        estilo = self.style.SUCCESS if cumple else self.style.WARNING
        self.stdout.write(estilo(
            f"RNF07 ({opciones['usuarios']} usuarios, respuesta bajo {LIMITE_CONCURRENCIA_SEGUNDOS:.0f} s en el 95% de los casos): {'cumple' if cumple else 'no cumple en este equipo'}"
        ))
