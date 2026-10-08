"""
Asistente virtual de AXZTRA (RF11, CU03 Consultar asistente virtual).

Funciona con reglas propias: corrige errores de escritura, detecta la intención de la consulta
y responde con el catálogo, las preguntas frecuentes y las sugerencias por rubro.
Nunca emite cotizaciones definitivas. Si se configura Botpress (AXZTRA_BOTPRESS_SCRIPTS),
las pantallas de solicitud cargan ese asistente en lugar de este.
"""

import difflib
import re
from urllib.parse import urlencode

from django.core.cache import cache
from django.urls import reverse

from .estimacion import PRECIO_BASE_POR_TIPO
from .recomendaciones import PERFILES_RUBRO, detectar_rubro, nombre_rubro, normalizar

PALABRAS_VACIAS = {
    'a', 'al', 'algo', 'como', 'con', 'cual', 'cuales', 'de', 'del', 'el', 'en', 'es', 'esta', 'este', 'hay', 'la', 'las',
    'le', 'lo', 'los', 'me', 'mi', 'mis', 'necesito', 'o', 'para', 'por', 'puedo', 'que', 'quiero', 'se', 'si', 'su', 'sus',
    'tengo', 'tu', 'tus', 'un', 'una', 'uno', 'y', 'ya', 'yo', 'hola', 'favor', 'saber', 'donde', 'cuando', 'hacer', 'ustedes',
}

PALABRAS_GENERICAS_SERVICIO = {'web', 'sitio', 'pagina', 'paginas', 'plan', 'servicio', 'online', 'linea', 'existente'}

PATRON_NUMERO = re.compile(r'axz\s*(\d{4})\s*(\d{4})')
PALABRAS_IDEAS = ['idea', 'ideas', 'recomienda', 'recomiendas', 'recomendacion', 'sugerencia', 'sugieres', 'deberia tener', 'que le pongo', 'que incluir', 'para mi negocio', 'para mi local', 'para mi empresa']


# Formatea un monto en pesos chilenos.
def _clp(valor):
    return '$' + f'{valor:,}'.replace(',', '.')


# Separa el texto en palabras normalizadas.
def _tokens(texto):
    return [t for t in normalizar(texto).split() if t not in PALABRAS_VACIAS and len(t) > 2]


# Base de conocimiento (servicios y preguntas frecuentes), guardada en caché.
def _conocimiento():
    from .models import PreguntaFrecuente, Servicio
    from .senales import version_catalogo

    # Arma la base de conocimiento desde la base de datos.
    def construir():
        preguntas = []
        for faq in PreguntaFrecuente.objects.filter(activa=True):
            claves = set(_tokens(faq.pregunta))
            for frase in faq.palabras_clave.split(','):
                claves.update(_tokens(frase))
            preguntas.append({'pregunta': faq.pregunta, 'respuesta': faq.respuesta, 'claves': claves})
        servicios = []
        for servicio in Servicio.objects.filter(activo=True):
            claves = set(_tokens(servicio.nombre))
            servicios.append({
                'nombre': servicio.nombre,
                'claves': (claves - PALABRAS_GENERICAS_SERVICIO) or claves,
                'precio': servicio.precio_base,
                'plazo': servicio.plazo_referencial,
                'url': servicio.get_absolute_url(),
                'resumen': servicio.resumen,
            })
        return {'preguntas': preguntas, 'servicios': servicios}

    return cache.get_or_set(f'axztra:asistente:{version_catalogo()}', construir, 600)


# Clase principal: recibe una pregunta y devuelve la respuesta, sugerencias y acciones.
class AsistenteVirtual:
    SALUDO = (
        'Hola, soy el asistente de AXZTRA. Puedo ayudarte a elegir un servicio, darte ideas para tu sitio, '
        'explicarte cómo se calcula la estimación o contarte en qué va tu solicitud. ¿Qué necesitas?'
    )

    SUGERENCIAS_INICIALES = [
        'Quiero crear una página web',
        '¿Cuánto cuesta una página?',
        'Ideas para una cafetería',
        '¿Cómo va mi solicitud?',
    ]

    def __init__(self, usuario=None):
        self.usuario = usuario if usuario is not None and usuario.is_authenticated else None

    # Lista de intenciones que reconoce el asistente y las palabras que las activan.
    def _intenciones(self):
        return [
            ('saludo', ['hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos'], self._saludo),
            ('agradecimiento', ['gracias', 'muchas gracias', 'genial', 'perfecto', 'excelente'], self._agradecimiento),
            ('soporte', ['no funciona', 'caido', 'caida', 'error', 'errores', 'problema', 'falla', 'hackeado', 'virus', 'lento', 'no carga', 'urgente', 'soporte', 'arreglar', 'roto'], self._soporte),
            ('mantenimiento', ['mantenimiento', 'mantener', 'respaldo', 'respaldos', 'backup', 'actualizacion', 'actualizaciones', 'monitoreo', 'mensual', 'plugins'], self._mantenimiento),
            ('mejora', ['mejorar', 'mejora', 'rediseno', 'redisenar', 'modernizar', 'optimizar', 'agregar', 'nueva seccion', 'ya tengo', 'mi sitio actual', 'seo', 'velocidad'], self._mejora),
            ('tienda', ['tienda online', 'tienda virtual', 'tienda', 'vender', 'venta', 'ecommerce', 'e commerce', 'carrito', 'webpay'], self._tienda),
            ('plazos', ['tiempo', 'plazo', 'demora', 'demoran', 'semanas', 'dias', 'entrega', 'rapido', 'tardan'], self._plazos),
            ('estimacion', ['precio', 'precios', 'cuanto', 'cuesta', 'cuestan', 'costo', 'valor', 'presupuesto', 'cotizar', 'estimacion', 'tarifa', 'plan', 'planes'], self._estimacion),
            ('creacion', ['crear', 'nueva pagina', 'pagina web', 'sitio web', 'sitio nuevo', 'desde cero', 'landing', 'hacer una pagina', 'necesito una pagina', 'quiero una pagina', 'web para mi'], self._creacion),
            ('seguimiento', ['seguimiento', 'estado', 'mi solicitud', 'mis solicitudes', 'avance', 'historial', 'como va', 'en que va'], self._seguimiento),
            ('pagos', ['pago', 'pagar', 'transferencia', 'tarjeta', 'factura', 'boleta', 'abono'], self._pagos),
            ('cuenta', ['registrar', 'registro', 'cuenta', 'contrasena', 'clave', 'iniciar sesion', 'login', 'ingresar'], self._cuenta),
            ('contacto', ['contacto', 'contactar', 'whatsapp', 'telefono', 'correo', 'email', 'hablar con', 'persona', 'humano', 'ejecutivo'], self._contacto),
            ('servicios', ['servicios', 'que hacen', 'que ofrecen', 'catalogo', 'ayuda', 'no se que necesito', 'no se que servicio', 'orientacion'], self._servicios),
            ('hosting', ['hosting', 'dominio', 'servidor', 'alojamiento', 'ssl', 'certificado'], self._hosting),
            ('aplicacion', ['app', 'apps', 'aplicacion', 'aplicaciones', 'android', 'iphone', 'play store', 'app store'], self._aplicacion),
        ]

    # Palabras conocidas, usadas para corregir errores de escritura.
    def _vocabulario(self, conocimiento):
        palabras = set()
        for _, claves, _ in self._intenciones():
            for clave in claves:
                palabras.update(clave.split())
        for faq in conocimiento['preguntas']:
            palabras.update(faq['claves'])
        for servicio in conocimiento['servicios']:
            palabras.update(servicio['claves'])
        return sorted(p for p in palabras if len(p) >= 5)

    # Corrige palabras mal escritas buscando la más parecida del vocabulario.
    def _corregir(self, texto, vocabulario):
        corregidas = []
        conjunto = set(vocabulario)
        for palabra in texto.split():
            if len(palabra) >= 5 and palabra not in conjunto:
                parecida = difflib.get_close_matches(palabra, vocabulario, n=1, cutoff=0.82)
                if parecida:
                    palabra = parecida[0]
            corregidas.append(palabra)
        return ' '.join(corregidas)

    # Punto de entrada: detecta la intención y llama al método que arma la respuesta.
    def responder(self, mensaje):
        texto = normalizar(mensaje)
        if not texto:
            return self._respuesta('vacio', 'Escribe tu consulta y te oriento con gusto.', self.SUGERENCIAS_INICIALES)

        numero = PATRON_NUMERO.search(texto.replace('-', ' '))
        if numero:
            return self._estado_solicitud(f'AXZ-{numero.group(1)}-{numero.group(2)}')

        conocimiento = _conocimiento()
        texto = self._corregir(texto, self._vocabulario(conocimiento))

        tokens = set(_tokens(texto))
        if tokens & {'cuanto', 'cuesta', 'cuestan', 'precio', 'precios', 'valor', 'costo', 'vale'}:
            servicio = self._servicio_mencionado(tokens, conocimiento)
            if servicio:
                return self._precio_servicio(servicio)

        rubro = detectar_rubro(texto)
        if rubro and (any(re.search(r'(^|\s)' + re.escape(p) + r'(\s|$)', texto) for p in PALABRAS_IDEAS) or len(texto.split()) <= 6):
            return self._ideas(rubro)

        mejor, mejor_puntaje = None, 0
        for _, claves, manejador in self._intenciones():
            puntaje = 0
            for clave in claves:
                if re.search(r'(^|\s)' + re.escape(clave) + r'(\s|$)', texto):
                    puntaje += 2 if ' ' in clave else 1
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = manejador, puntaje

        faq, faq_puntaje = None, 0
        for pregunta in conocimiento['preguntas']:
            coincidencias = len(tokens & pregunta['claves'])
            if coincidencias > faq_puntaje:
                faq, faq_puntaje = pregunta, coincidencias
        if faq is not None and faq_puntaje >= 2 and faq_puntaje >= mejor_puntaje:
            return self._respuesta('pregunta_frecuente', faq['respuesta'], ['¿Cuánto cuesta una página?', 'Hablar con una persona'])

        if mejor is None:
            servicio = self._servicio_mencionado(tokens, conocimiento)
            if servicio:
                return self._precio_servicio(servicio)
            return self._no_entendido()
        return mejor()

    # Detecta si la pregunta nombra un servicio del catálogo.
    def _servicio_mencionado(self, tokens, conocimiento):
        mejor, puntaje_mejor = None, 0
        for servicio in conocimiento['servicios']:
            puntaje = len(tokens & servicio['claves'])
            if puntaje > puntaje_mejor and puntaje >= max(1, len(servicio['claves']) // 2):
                mejor, puntaje_mejor = servicio, puntaje
        return mejor

    # Formato común de respuesta (texto, sugerencias y acciones).
    def _respuesta(self, intencion, texto, sugerencias=None, acciones=None):
        return {
            'intencion': intencion,
            'respuesta': texto,
            'sugerencias': sugerencias or [],
            'acciones': acciones or [],
        }

    # Botón de acción que se muestra bajo la respuesta (por ejemplo, ir al formulario).
    def _accion(self, texto, destino, parametros=None):
        url = destino if destino.startswith('/') else reverse(destino)
        if parametros:
            url = f'{url}?{urlencode(parametros, doseq=True)}'
        return {'texto': texto, 'url': url}

    # Responde cómo va una solicitud del cliente que inició sesión.
    def _estado_solicitud(self, numero):
        from .models import Solicitud

        if not self.usuario:
            return self._respuesta(
                'seguimiento',
                f'Para revisar la solicitud {numero} necesitas iniciar sesión con la cuenta que la creó.',
                [],
                [self._accion('Iniciar sesión', 'login')],
            )
        consulta = Solicitud.objects.select_related('estado', 'responsable')
        if not self.usuario.is_staff:
            consulta = consulta.filter(cliente=self.usuario)
        solicitud = consulta.filter(numero=numero).first()
        if solicitud is None:
            return self._respuesta(
                'seguimiento',
                f'No encontré la solicitud {numero} en tu cuenta. Revisa el número o entra a "Mis solicitudes".',
                [],
                [self._accion('Ir a mis solicitudes', 'mis_solicitudes')],
            )
        partes = [f'La solicitud {solicitud.numero} ({solicitud.titulo}) está en estado {solicitud.estado.nombre}.']
        if solicitud.estado.descripcion:
            partes.append(solicitud.estado.descripcion)
        if solicitud.responsable_id:
            partes.append(f'Responsable: {solicitud.responsable.get_full_name() or solicitud.responsable.email}.')
        return self._respuesta(
            'seguimiento',
            ' '.join(partes),
            [],
            [self._accion('Ver la solicitud', solicitud.get_absolute_url())],
        )

    # Ideas de funcionalidades según el rubro del negocio.
    def _ideas(self, rubro):
        perfil = PERFILES_RUBRO[rubro]
        parametros = {
            'tipo_sitio': perfil['tipo_sitio'],
            'funcionalidades': perfil['funcionalidades'],
            'integraciones': perfil['integraciones'],
            'rubro': rubro,
        }
        return self._respuesta(
            'ideas',
            f'Para un sitio de {nombre_rubro(rubro).lower()} suele funcionar bien incluir {perfil["ideas"]}. '
            'Puedo dejar esas opciones marcadas en el formulario para que veas la estimación y ajustes lo que quieras.',
            ['¿Cuánto se demoran?', '¿Cómo se calcula el precio?'],
            [self._accion('Estimar con estas opciones', 'crear_web', parametros)],
        )

    # Precio referencial de un servicio mencionado.
    def _precio_servicio(self, servicio):
        if servicio['precio']:
            texto = f'{servicio["nombre"]}: {servicio["resumen"]} Parte desde {_clp(servicio["precio"])} más IVA'
        else:
            texto = f'{servicio["nombre"]}: {servicio["resumen"]} El valor se define en la cotización'
        if servicio['plazo']:
            texto += f', con un plazo referencial de {servicio["plazo"].lower()}'
        texto += '. El valor final lo confirma el equipo en la cotización formal.'
        return self._respuesta(
            'servicio',
            texto,
            ['¿Cuánto se demoran?', 'Hablar con una persona'],
            [self._accion('Ver el servicio', servicio['url'])],
        )

    def _saludo(self):
        nombre = f' {self.usuario.first_name}' if self.usuario and self.usuario.first_name else ''
        texto = self.SALUDO.replace('Hola,', f'Hola{nombre},', 1)
        return self._respuesta('saludo', texto, self.SUGERENCIAS_INICIALES)

    def _agradecimiento(self):
        return self._respuesta(
            'agradecimiento',
            'Con gusto. Si te surge otra duda, escríbeme por aquí.',
            ['Quiero crear una página web', '¿Cómo va mi solicitud?'],
        )

    def _creacion(self):
        return self._respuesta(
            'creacion',
            'Para un sitio nuevo te recomiendo el servicio de creación de página web. '
            'El formulario tiene tres pasos: información básica, tu negocio y funcionalidades. '
            'Mientras avanzas verás la estimación de precio y plazo actualizada en todo momento.',
            ['Ideas para mi negocio', '¿Cuánto se demoran?'],
            [self._accion('Crear mi página web', 'crear_web')],
        )

    def _tienda(self):
        return self._respuesta(
            'tienda',
            'Para vender en línea elige el tipo de sitio "Tienda online" y marca las funcionalidades '
            '"Carrito y checkout" y "Pasarela de pago". Una tienda parte desde '
            f'{_clp(PRECIO_BASE_POR_TIPO["tienda"])} más las funcionalidades que agregues.',
            ['¿Cuánto se demoran?', '¿Qué medios de pago aceptan?'],
            [self._accion('Estimar mi tienda', 'crear_web', {'tipo_sitio': 'tienda', 'funcionalidades': ['catalogo', 'tienda'], 'integraciones': ['pagos']})],
        )

    def _estimacion(self):
        return self._respuesta(
            'estimacion',
            'La estimación se calcula así: precio base según el tipo de sitio, más cada funcionalidad '
            'e integración multiplicada por un factor de complejidad (1,0 básica, 1,25 media y 1,5 alta). '
            f'Como referencia, una landing page parte desde {_clp(PRECIO_BASE_POR_TIPO["landing"])} y un sitio corporativo '
            f'desde {_clp(PRECIO_BASE_POR_TIPO["corporativo"])}. El valor es orientativo: la cotización formal la emite el equipo tras revisar tu caso.',
            ['Quiero crear una página web', '¿Cuánto se demoran?'],
            [self._accion('Calcular mi estimación', 'crear_web'), self._accion('Ver servicios', 'catalogo')],
        )

    def _plazos(self):
        return self._respuesta(
            'plazos',
            'Los plazos habituales son: proyectos básicos de 1 a 2 semanas, medianos de 3 a 5 semanas '
            'y complejos de 5 a 8 semanas. Las tiendas online suman cerca de una semana. '
            'Las solicitudes de soporte se responden dentro del siguiente día hábil, o antes si son urgentes.',
            ['¿Cuánto cuesta una página?', 'Mi sitio tiene un problema'],
        )

    def _mejora(self):
        return self._respuesta(
            'mejora',
            'Si ya tienes un sitio, el servicio adecuado es la mejora de página existente: rediseño, '
            'optimización de velocidad y SEO, o nuevas secciones y funciones. En la solicitud indica la dirección '
            'de tu sitio y qué te gustaría cambiar.',
            ['¿Cuánto cuesta una página?', 'Necesito mantenimiento'],
            [self._accion('Solicitar una mejora', 'solicitar_mejora')],
        )

    def _soporte(self):
        return self._respuesta(
            'soporte',
            'Crea una solicitud de soporte técnico con la dirección del sitio, qué ocurre y desde cuándo. '
            'Puedes adjuntar capturas de pantalla. Si el sitio está caído o afecta tus ventas, marca la prioridad '
            'como urgente para que el equipo la atienda primero.',
            ['¿Cómo va mi solicitud?', 'Hablar con una persona'],
            [self._accion('Pedir soporte técnico', 'solicitar_soporte')],
        )

    def _mantenimiento(self):
        return self._respuesta(
            'mantenimiento',
            'El mantenimiento incluye respaldos periódicos, actualizaciones de seguridad, monitoreo de disponibilidad '
            'y cambios menores de contenido. Puedes elegir una frecuencia mensual o trimestral al crear la solicitud.',
            ['Mi sitio tiene un problema', '¿Cuánto cuesta el mantenimiento?'],
            [self._accion('Solicitar mantenimiento', 'solicitar_mantenimiento')],
        )

    def _seguimiento(self):
        if self.usuario:
            from .models import Solicitud

            activas = list(
                Solicitud.objects.filter(cliente=self.usuario, estado__es_final=False)
                .select_related('estado')
                .order_by('-fecha_actualizacion')[:3]
            )
            if activas:
                detalle = '; '.join(f'{s.numero} ({s.estado.nombre})' for s in activas)
                texto = f'Tienes {len(activas)} solicitud{"es" if len(activas) != 1 else ""} en curso: {detalle}. Escríbeme el número de una para ver su detalle.'
            else:
                texto = 'No tienes solicitudes en curso. Cuando envíes una, verás aquí su estado y el historial de cambios.'
            return self._respuesta('seguimiento', texto, [], [self._accion('Ir a mis solicitudes', 'mis_solicitudes')])
        return self._respuesta(
            'seguimiento',
            'Para seguir tus solicitudes necesitas una cuenta. Al ingresar verás el estado, el historial, los mensajes y las cotizaciones de cada una.',
            [],
            [self._accion('Iniciar sesión', 'login'), self._accion('Crear cuenta', 'registro')],
        )

    def _pagos(self):
        return self._respuesta(
            'pagos',
            'Por ahora la plataforma no procesa pagos en línea. Las condiciones y medios de pago '
            'se acuerdan en la cotización formal que emite el equipo.',
            ['¿Cuánto cuesta una página?', 'Hablar con una persona'],
        )

    def _cuenta(self):
        if self.usuario:
            return self._respuesta(
                'cuenta',
                'Ya iniciaste sesión. En "Mis datos" puedes actualizar tu información, cambiar tu contraseña o descargar una copia de tus datos.',
                [],
                [self._accion('Ir a mis datos', 'mi_cuenta')],
            )
        return self._respuesta(
            'cuenta',
            'Puedes explorar los servicios sin cuenta. Para enviar una solicitud o ver su estado, regístrate con tu correo. '
            'Si olvidaste tu contraseña, usa la opción "¿Olvidaste tu contraseña?" en la página de ingreso.',
            [],
            [self._accion('Crear cuenta', 'registro'), self._accion('Iniciar sesión', 'login')],
        )

    def _contacto(self):
        return self._respuesta(
            'contacto',
            'Puedes hablar directamente con el equipo por WhatsApp con el botón verde de la esquina inferior. '
            'Si ya tienes una solicitud, escríbenos desde su sección de mensajes para que la conversación quede registrada.',
            ['Quiero crear una página web', 'Mi sitio tiene un problema'],
        )

    def _servicios(self):
        return self._respuesta(
            'servicios',
            'Ofrecemos cuatro servicios: creación de página web, mejora de página existente, '
            'soporte técnico y mantenimiento periódico. Cuéntame qué necesitas o a qué se dedica tu negocio y te indico qué conviene.',
            ['Quiero crear una página web', 'Quiero mejorar mi sitio', 'Mi sitio tiene un problema', 'Necesito mantenimiento'],
            [self._accion('Ver catálogo', 'catalogo')],
        )

    def _hosting(self):
        return self._respuesta(
            'hosting',
            'Te orientamos en la contratación de dominio, hosting y certificado SSL, y dejamos tu sitio publicado. '
            'Indícalo en los comentarios de tu solicitud para incluirlo en la cotización.',
            ['Quiero crear una página web', 'Necesito mantenimiento'],
        )

    def _aplicacion(self):
        return self._respuesta(
            'aplicacion',
            'Nos especializamos en sitios web que funcionan en cualquier celular, tablet o computador, sin necesidad de instalar nada. '
            'Las aplicaciones nativas para Android o iPhone no están en el catálogo actual, pero cuéntanos tu idea por WhatsApp y evaluamos la mejor alternativa.',
            ['Quiero crear una página web', 'Hablar con una persona'],
        )

    def _no_entendido(self):
        return self._respuesta(
            'no_entendido',
            'No estoy seguro de haber entendido. Puedo ayudarte con servicios, precios referenciales, plazos, '
            'ideas para tu sitio, soporte o el seguimiento de tus solicitudes. También puedes escribir al equipo por WhatsApp.',
            self.SUGERENCIAS_INICIALES,
        )
