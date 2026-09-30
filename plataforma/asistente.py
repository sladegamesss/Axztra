import re
import unicodedata

from django.urls import reverse

from .estimacion import PRECIO_BASE_POR_TIPO


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', (texto or '').lower())
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9ñ\s]', ' ', texto)).strip()


def _clp(valor):
    return '$' + f'{valor:,}'.replace(',', '.')


class AsistenteVirtual:
    SALUDO = (
        'Hola, soy el asistente de AXZTRA. Puedo orientarte para elegir un servicio, '
        'explicarte cómo se calcula la estimación o ayudarte a completar tu solicitud. ¿Qué necesitas?'
    )

    SUGERENCIAS_INICIALES = [
        'Quiero crear una página web',
        '¿Cuánto cuesta una página?',
        'Mi sitio tiene un problema',
        '¿Cómo sigo mi solicitud?',
    ]

    def __init__(self, usuario=None):
        self.usuario = usuario if usuario is not None and usuario.is_authenticated else None

    def _intenciones(self):
        return [
            ('saludo', ['hola', 'buenas', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos', 'hey'], self._saludo),
            ('agradecimiento', ['gracias', 'muchas gracias', 'genial', 'perfecto', 'excelente'], self._agradecimiento),
            ('soporte', ['no funciona', 'caido', 'caida', 'error', 'problema', 'falla', 'hackeado', 'virus', 'lento', 'no carga', 'urgente', 'soporte', 'arreglar', 'roto'], self._soporte),
            ('mantenimiento', ['mantenimiento', 'mantener', 'respaldo', 'backup', 'actualizacion', 'actualizaciones', 'monitoreo', 'mensual', 'plugins'], self._mantenimiento),
            ('mejora', ['mejorar', 'mejora', 'rediseno', 'redisenar', 'modernizar', 'optimizar', 'agregar', 'nueva seccion', 'ya tengo', 'mi sitio actual', 'seo', 'velocidad'], self._mejora),
            ('tienda', ['tienda online', 'tienda virtual', 'tienda', 'vender', 'venta', 'ecommerce', 'e commerce', 'carrito', 'productos en linea', 'webpay'], self._tienda),
            ('plazos', ['tiempo', 'plazo', 'demora', 'demoran', 'cuando', 'semanas', 'dias', 'entrega', 'rapido'], self._plazos),
            ('estimacion', ['precio', 'precios', 'cuanto', 'cuesta', 'costo', 'valor', 'presupuesto', 'cotizar', 'cotizacion', 'estimacion', 'tarifa', 'plan', 'planes'], self._estimacion),
            ('creacion', ['crear', 'nueva pagina', 'pagina web', 'sitio web', 'sitio nuevo', 'desde cero', 'landing', 'hacer una pagina', 'necesito una pagina', 'quiero una pagina', 'web para mi'], self._creacion),
            ('seguimiento', ['seguimiento', 'estado', 'mi solicitud', 'mis solicitudes', 'avance', 'historial', 'donde veo'], self._seguimiento),
            ('pagos', ['pago', 'pagar', 'transferencia', 'tarjeta', 'factura', 'boleta', 'abono'], self._pagos),
            ('cuenta', ['registrar', 'registro', 'cuenta', 'contrasena', 'clave', 'iniciar sesion', 'login', 'ingresar'], self._cuenta),
            ('contacto', ['contacto', 'contactar', 'whatsapp', 'telefono', 'correo', 'email', 'hablar con', 'persona', 'humano', 'ejecutivo'], self._contacto),
            ('servicios', ['servicios', 'que hacen', 'que ofrecen', 'catalogo', 'ayuda', 'no se que necesito', 'no se que servicio', 'orientacion'], self._servicios),
            ('hosting', ['hosting', 'dominio', 'servidor', 'alojamiento', 'ssl', 'certificado'], self._hosting),
        ]

    def responder(self, mensaje):
        texto = normalizar(mensaje)
        if not texto:
            return self._respuesta('vacio', 'Escribe tu consulta y te oriento con gusto.', self.SUGERENCIAS_INICIALES)

        mejor = None
        mejor_puntaje = 0
        for nombre, claves, manejador in self._intenciones():
            puntaje = 0
            for clave in claves:
                if re.search(r'(^|\s)' + re.escape(clave) + r'(\s|$)', texto):
                    puntaje += 2 if ' ' in clave else 1
            if puntaje > mejor_puntaje:
                mejor, mejor_puntaje = manejador, puntaje

        if mejor is None:
            return self._no_entendido()
        return mejor()

    def _respuesta(self, intencion, texto, sugerencias=None, acciones=None):
        return {
            'intencion': intencion,
            'respuesta': texto,
            'sugerencias': sugerencias or [],
            'acciones': acciones or [],
        }

    def _accion(self, texto, nombre_url):
        return {'texto': texto, 'url': reverse(nombre_url)}

    def _saludo(self):
        nombre = f' {self.usuario.first_name}' if self.usuario and self.usuario.first_name else ''
        texto = self.SALUDO.replace('Hola,', f'Hola{nombre},', 1)
        return self._respuesta('saludo', texto, self.SUGERENCIAS_INICIALES)

    def _agradecimiento(self):
        return self._respuesta(
            'agradecimiento',
            'Con gusto. Si te surge otra duda, escríbeme por aquí.',
            ['Quiero crear una página web', '¿Cómo sigo mi solicitud?'],
        )

    def _creacion(self):
        return self._respuesta(
            'creacion',
            'Para un sitio nuevo te recomiendo el servicio de Creación de página web. '
            'El formulario tiene tres pasos: información de tu negocio, objetivos y funcionalidades. '
            'Al terminar verás una estimación referencial de precio y plazo antes de enviar la solicitud.',
            ['¿Cuánto cuesta una página?', '¿Cuánto se demoran?'],
            [self._accion('Crear mi página web', 'crear_web')],
        )

    def _tienda(self):
        return self._respuesta(
            'tienda',
            'Para vender en línea elige el tipo de sitio "Tienda online" y marca las funcionalidades '
            '"Carrito y checkout" y "Pasarela de pago". Una tienda parte desde '
            f'{_clp(PRECIO_BASE_POR_TIPO["tienda"])} más las funcionalidades que agregues. '
            'La estimación final la verás al completar el formulario.',
            ['¿Cuánto se demoran?', '¿Qué medios de pago aceptan?'],
            [self._accion('Cotizar mi tienda', 'crear_web')],
        )

    def _estimacion(self):
        return self._respuesta(
            'estimacion',
            'La estimación se calcula así: precio base según el tipo de sitio, más cada funcionalidad '
            'e integración multiplicada por un factor de complejidad (1,0 básica, 1,25 media y 1,5 alta). '
            f'Como referencia, una landing page parte desde {_clp(PRECIO_BASE_POR_TIPO["landing"])} y un sitio corporativo '
            f'desde {_clp(PRECIO_BASE_POR_TIPO["corporativo"])}. El valor es orientativo: la cotización formal la emite nuestro equipo tras revisar tu caso.',
            ['Quiero crear una página web', '¿Cuánto se demoran?'],
            [self._accion('Calcular mi estimación', 'crear_web'), self._accion('Ver servicios', 'catalogo')],
        )

    def _plazos(self):
        return self._respuesta(
            'plazos',
            'Los plazos habituales son: proyectos básicos de 1 a 2 semanas, medianos de 3 a 5 semanas '
            'y complejos de 5 a 8 semanas. Las tiendas online suman cerca de una semana. '
            'Para soporte técnico respondemos dentro del siguiente día hábil, o antes si marcas la solicitud como urgente.',
            ['¿Cuánto cuesta una página?', 'Mi sitio tiene un problema'],
        )

    def _mejora(self):
        return self._respuesta(
            'mejora',
            'Si ya tienes un sitio, el servicio adecuado es Mejora de página existente: rediseño, '
            'optimización de velocidad y SEO, o nuevas secciones y funciones. En la solicitud indica la dirección '
            'de tu sitio y qué te gustaría cambiar.',
            ['¿Cuánto cuesta una página?', 'Necesito mantenimiento'],
            [self._accion('Solicitar una mejora', 'solicitar_mejora')],
        )

    def _soporte(self):
        return self._respuesta(
            'soporte',
            'Lamento el inconveniente. Crea una solicitud de Soporte técnico indicando la dirección del sitio, '
            'qué ocurre y desde cuándo. Si el sitio está caído o afecta tus ventas, marca la prioridad como urgente '
            'para que el equipo la atienda primero.',
            ['¿Cómo sigo mi solicitud?', 'Hablar con una persona'],
            [self._accion('Pedir soporte técnico', 'solicitar_soporte')],
        )

    def _mantenimiento(self):
        return self._respuesta(
            'mantenimiento',
            'El mantenimiento incluye respaldos periódicos, actualizaciones de seguridad, monitoreo de disponibilidad '
            'y pequeños cambios de contenido. Puedes elegir una frecuencia mensual o trimestral al crear la solicitud.',
            ['Mi sitio tiene un problema', '¿Cuánto cuesta una página?'],
            [self._accion('Solicitar mantenimiento', 'solicitar_mantenimiento')],
        )

    def _seguimiento(self):
        if self.usuario:
            return self._respuesta(
                'seguimiento',
                'En "Mis solicitudes" verás cada solicitud con su estado actual, el historial de cambios, '
                'la estimación y, cuando esté lista, la cotización formal para aceptarla o rechazarla. '
                'También te avisamos por correo cada vez que cambia el estado.',
                [],
                [self._accion('Ir a mis solicitudes', 'mis_solicitudes')],
            )
        return self._respuesta(
            'seguimiento',
            'Para seguir tus solicitudes necesitas una cuenta. Al ingresar verás el estado, el historial y las cotizaciones de cada una.',
            [],
            [self._accion('Iniciar sesión', 'login'), self._accion('Crear cuenta', 'registro')],
        )

    def _pagos(self):
        return self._respuesta(
            'pagos',
            'Por ahora la plataforma no procesa pagos en línea. Las condiciones y medios de pago '
            '(transferencia bancaria u otros) se acuerdan en la cotización formal que emite nuestro equipo.',
            ['¿Cuánto cuesta una página?', 'Hablar con una persona'],
        )

    def _cuenta(self):
        if self.usuario:
            return self._respuesta(
                'cuenta',
                'Ya iniciaste sesión. En "Mi cuenta" puedes actualizar tus datos de contacto y preferencias de notificación.',
                [],
                [self._accion('Ir a mi cuenta', 'mi_cuenta')],
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
            'Puedes hablar directamente con el equipo por WhatsApp con el botón verde de la esquina inferior, '
            'o dejar tu consulta en una solicitud para que quede registrada y con seguimiento.',
            ['Quiero crear una página web', 'Mi sitio tiene un problema'],
        )

    def _servicios(self):
        return self._respuesta(
            'servicios',
            'Ofrecemos cuatro servicios: Creación de página web (sitios nuevos), Mejora de página existente, '
            'Soporte técnico para incidencias y Mantenimiento periódico. Cuéntame qué necesitas y te indico cuál conviene.',
            ['Quiero crear una página web', 'Quiero mejorar mi sitio', 'Mi sitio tiene un problema', 'Necesito mantenimiento'],
            [self._accion('Ver catálogo', 'catalogo')],
        )

    def _hosting(self):
        return self._respuesta(
            'hosting',
            'Podemos orientarte en la contratación de dominio, hosting y certificado SSL, y dejar tu sitio publicado. '
            'Indícalo en las observaciones de tu solicitud para incluirlo en la cotización.',
            ['Quiero crear una página web', 'Necesito mantenimiento'],
        )

    def _no_entendido(self):
        return self._respuesta(
            'no_entendido',
            'No estoy seguro de haber entendido. Puedo ayudarte con servicios, precios referenciales, plazos, '
            'soporte o el seguimiento de tus solicitudes. También puedes escribir al equipo por WhatsApp.',
            self.SUGERENCIAS_INICIALES,
        )
