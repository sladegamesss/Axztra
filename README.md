# AXZTRA

Plataforma web para contratar y gestionar servicios de desarrollo web: creación de sitios, mejoras, soporte técnico y mantenimiento. Los clientes describen su proyecto con un formulario guiado, obtienen una estimación referencial al instante, reciben la cotización formal y siguen cada etapa en línea. El equipo trabaja las solicitudes desde un panel protegido con verificación en dos pasos.

Proyecto del Taller de Sistemas de Información II, Universidad Técnica Federico Santa María.
Equipo: Benjamín Ruiz, Camilo Barra y Franco Constanzo. Docentes: Johanna Schorwer y Gerlys Villalobos.

## Guía del código

El archivo `docs/GUIA_DEL_PROYECTO.md` relaciona cada caso de uso, tabla y diagrama del Informe Final de Diseño con su archivo en el código. Además, cada archivo del proyecto tiene comentarios que explican qué hace y a qué parte del informe corresponde.

## Puesta en marcha (Windows)

Requiere Python 3.12 y PostgreSQL. Una sola vez:

1. Instalar PostgreSQL desde https://www.postgresql.org/download/windows/ (puerto 5432; anotar la contraseña del usuario `postgres`).
2. Abrir pgAdmin (se instala junto con PostgreSQL), clic derecho en Databases, Create, Database, y crear una base llamada `axztra`.
3. En la carpeta del proyecto, copiar `.env.example` como `.env` y escribir en él la contraseña elegida en `POSTGRES_PASSWORD`.

Luego, en PowerShell, dentro de la carpeta que contiene `manage.py`:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py comprobar_base
python manage.py migrate
python manage.py datos_demo
python manage.py runserver
```

`comprobar_base` confirma que la conexión funciona y, si no, explica qué revisar.

Luego abrir http://127.0.0.1:8000. En Linux o macOS la activación es `source venv/bin/activate`.

Si PowerShell bloquea la activación del entorno, ejecutar una vez `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

### Cuentas de demostración

| Rol | Correo | Contraseña | Acceso |
|-----|--------|------------|--------|
| Administrador | admin@axztra.cl | AxztraAdmin2026 | Panel completo, configuración y administración de datos |
| Equipo (desarrollo) | desarrollo@axztra.cl | Equipo2026 | Solicitudes, catálogo y contenido del sitio |
| Equipo (soporte) | soporte@axztra.cl | Equipo2026 | Solicitudes, tablero y clientes |
| Cliente | cliente@axztra.cl | Cliente2026 | Solicitudes con cotización pendiente, mensajes y archivos |

Otros clientes de ejemplo usan la misma contraseña `Cliente2026`: carlos.perez@axztra.cl, fundacion.vida@axztra.cl, andrea.rojas@axztra.cl y jorge.soto@axztra.cl.

Todos los usuarios, clientes y equipo, ingresan con su contraseña y un código de 6 dígitos enviado por correo. En desarrollo los correos se muestran en la terminal donde corre el servidor. El comando `datos_demo` se puede ejecutar varias veces sin duplicar información; con `--reiniciar` vuelve a crear las solicitudes de ejemplo.

## Funcionalidades principales

Para clientes:

- Catálogo de servicios con búsqueda, filtros por tipo y categoría, y ficha de cada servicio.
- Estimador en la portada que calcula precio y plazo mientras se eligen opciones.
- Formulario guiado de cuatro pasos para crear un sitio (proyecto, negocio, funcionalidades y diseño), con resumen de precio en vivo y sugerencias de funcionalidades según el rubro del negocio. El último paso recoge estilo visual, colores, secciones, sitios de referencia, logo, dominio, presupuesto y forma de contacto preferida.
- Formularios breves para mejoras, soporte técnico y mantenimiento, con archivo adjunto y vínculo a una solicitud anterior.
- Seguimiento de cada solicitud: etapas, historial, responsable asignado, mensajes con el equipo y archivos compartidos.
- Cotización formal con detalle por ítem, IVA, vigencia y documento imprimible; se acepta o rechaza desde la plataforma.
- Asistente virtual en las pantallas para crear una solicitud: orienta sobre servicios, precios, plazos, ideas por rubro y estado de solicitudes.
- Cuenta personal: datos, cambio de contraseña, descarga de todos los datos en JSON y eliminación de la cuenta.

Para el equipo:

- Resumen con solicitudes abiertas, plazos de respuesta vencidos, ingresos por cotizaciones aceptadas, tasa de aceptación y gráficos por mes, estado y tipo.
- Listado con filtros por estado, tipo, prioridad, responsable y plazo vencido, más exportación a CSV compatible con Excel.
- Tablero por etapas donde las solicitudes se mueven arrastrando tarjetas.
- Ficha de solicitud con cambio de estado, asignación de responsable, prioridad, notas internas, conversación con el cliente, archivos y emisión de cotizaciones por ítems con versiones.
- Administración del catálogo, las preguntas frecuentes, los datos de contacto y un aviso destacado del sitio, sin tocar código.
- Clientes con exportación a CSV, consultas hechas al asistente y registro de actividad para auditoría.
- Permisos por rol: todo el equipo gestiona solicitudes; el catálogo, el contenido y la auditoría requieren permisos específicos.

Experiencia de uso y accesibilidad:

- Identidad visual en negro profundo con acentos en degradado dorado, naranja y magenta; logo, favicon e imagen para compartir el sitio en redes y WhatsApp.
- Botón Inicio siempre visible: en el menú principal, en la cabecera de tablets, en la barra inferior de los celulares y como primer paso de las migas de pan.
- Botón para cambiar el tamaño del texto (normal, grande y muy grande) en la cabecera y en el menú del celular; se recuerda en el navegador y el menú se reorganiza para que nada quede cortado.
- Barra inferior en celulares con Inicio, Servicios, Solicitar, Mis solicitudes o Ingresar y Contacto, al alcance del pulgar.
- Botón para mostrar la contraseña, mensajes de error en español junto a cada campo, indicador de carga al enviar formularios y avisos que se cierran solos.
- Íconos acompañados de texto en todos los accesos y áreas táctiles de al menos 44 píxeles.
- Animaciones visibles y cuidadas: título que aparece palabra por palabra, luces de color en movimiento en la portada, borde de luz que gira en el estimador, cinta de servicios en desplazamiento, secciones que aparecen al bajar, tarjetas con un brillo que sigue al cursor, botones con destello, montos y contadores que suben hasta su valor, gráficos que crecen, barra de avance de lectura y preguntas frecuentes que se abren con suavidad. Se desactivan automáticamente cuando el sistema operativo pide reducir el movimiento.

## Requisitos del informe

| Requisito | Cómo se cumple |
|-----------|----------------|
| RF01 Consultar catálogo | Catálogo con búsqueda y filtros, ficha por servicio, servicios destacados en la portada y mapa del sitio para buscadores. |
| RF02 Gestionar autenticación | Registro con aceptación de términos, ingreso por correo, recuperación de contraseña, cambio de contraseña y bloqueo temporal tras intentos fallidos. |
| RF03 Gestionar solicitudes de servicio | Selector de los cuatro tipos de servicio con formularios específicos y numeración correlativa AXZ-AAMM-NNNN. |
| RF04 Levantar requerimientos | Formulario guiado por pasos, validación inmediata y sugerencias de funcionalidades generadas a partir de la descripción del negocio. |
| RF05 Estimación referencial | Cálculo por reglas con desglose, rango de precio y plazo; el mismo cálculo corre en el navegador y en el servidor con resultados idénticos. |
| RF06 Solicitar y registrar cotización | Cotización formal por ítems con IVA, vigencia, versiones, documento imprimible y respuesta del cliente. |
| RF07 Consultar información del cliente | Estado, etapas, historial, mensajes, archivos, cotización y solicitudes relacionadas; descarga de datos personales. |
| RF08 Notificaciones | Correos al registrar una solicitud, cambiar su estado, emitir o responder una cotización, recibir mensajes, asignar responsables y cancelar. El envío es asíncrono. |
| RF09 Gestionar servicios y categorías | Alta, edición, publicación y ocultamiento desde el panel, con efecto inmediato en el sitio. |
| RF10 Gestionar solicitudes y estados | Flujo de estados con reglas de transición, tablero, responsables, prioridades, plazos de respuesta y cotización definitiva emitida solo por el equipo. |
| RF11 Asistente virtual | Asistente con detección de intención, corrección de errores de escritura, respuestas desde las preguntas frecuentes, precios del catálogo e ideas por rubro. Nunca emite cotizaciones definitivas. |
| RF12 Preparar integraciones | API REST versionada con tokens para sistemas externos (facturación, pagos, CRM) y punto de conexión para un asistente externo como Botpress. |
| RNF01 Usabilidad | Una solicitud completa se envía en menos de 5 minutos: cuatro pasos, opciones visuales, textos de ayuda y resumen permanente. Botón Inicio visible y barra inferior en celulares. |
| RNF02 Diseño adaptable | Revisado sin desbordes en anchos de 320, 390, 768, 1366, 2560 y 3840 píxeles y con los tres tamaños de texto. |
| RNF03 Integridad | Transacciones atómicas, restricciones de verificación y unicidad en la base de datos, correos únicos sin distinguir mayúsculas, solicitudes protegidas ante borrados y protección contra envíos repetidos del mismo formulario. |
| RNF04 Verificación en dos pasos | Código de un solo uso por correo, con vencimiento de 10 minutos y máximo 5 intentos, para clientes y equipo (también confirma el correo al registrarse). Se puede desactivar solo para clientes con `AXZTRA_VERIFICACION_CLIENTES=0`. |
| RNF05 Validación en el navegador | Los mensajes en español aparecen de inmediato: la validación toma menos de 2 ms en el navegador, bajo el límite de 0,3 s. |
| RNF06 Tiempo de carga | Respuestas del servidor entre 3 y 55 ms por página con más de 3.000 solicitudes en la base. |
| RNF07 Concurrencia | 300 usuarios simultáneos: 1.500 peticiones sin errores, mediana de 1,69 s y P95 de 1,73 s en un equipo de un núcleo. |
| RNF08 Nuevas categorías y tipos | Categorías, servicios y preguntas frecuentes se crean desde el panel en minutos; un nuevo tipo de solicitud requiere un formulario adicional en `forms.py`. |

## Arquitectura

Aplicación Django organizada en el proyecto `axztra` (configuración) y la aplicación `plataforma`:

| Módulo | Responsabilidad |
|--------|-----------------|
| `models.py` | Servicios, categorías, perfiles, solicitudes, estados, estimaciones, cotizaciones, mensajes, adjuntos, preguntas frecuentes, configuración del sitio, auditoría y tokens de API. |
| `gestion.py` | Reglas de negocio: creación de solicitudes, transiciones de estado, cotizaciones, asignaciones, mensajes y archivos, siempre dentro de transacciones. |
| `estimacion.py` | Tarifas y cálculo de la estimación referencial. |
| `asistente.py`, `recomendaciones.py` | Asistente virtual y sugerencias por rubro. |
| `notificaciones.py` | Correos transaccionales con envío en segundo plano. |
| `seguridad.py`, `verificacion.py`, `auditoria.py` | Cabeceras de seguridad, límites de peticiones, verificación en dos pasos y registro de actividad. |
| `views/` | Vistas públicas, de cuenta, del cliente, del panel y del asistente. |
| `api/` | API de integración versionada en `/api/v1/`. |
| `templates/`, `static/` | Interfaz propia sin frameworks externos; íconos incluidos en el proyecto. |

El catálogo, las preguntas frecuentes, los estados y la configuración del sitio se guardan en caché y se invalidan automáticamente al modificarse. Los listados usan consultas agregadas para evitar consultas repetidas por fila.

## Base de datos

El modelo se diseñó para que la información no quede incoherente aunque falle un formulario o dos personas actúen al mismo tiempo:

- Restricciones en la propia base de datos: prioridades, tipos y estados válidos, páginas entre 1 y 60, rangos de estimación coherentes, plazos y vigencias mayores que cero, mensajes con texto y un único registro de configuración.
- Unicidad: número de solicitud, token de envío, nombres de servicio y preguntas frecuentes sin repetir (sin distinguir mayúsculas) y un índice único que impide dos cuentas con el mismo correo.
- Las solicitudes quedan protegidas: no se puede borrar un cliente que tiene solicitudes; al eliminar una cuenta se anonimizan sus datos personales. Al borrar un adjunto también se elimina su archivo.
- Índices para las consultas frecuentes: solicitudes por estado, cliente, responsable, tipo, prioridad y fecha; mensajes sin leer; historial; registro de actividad; y búsqueda de correos.
- Todas las operaciones de negocio corren dentro de transacciones y los correos se envían solo después de confirmarse los cambios.

Revisión realizada con SQLite: `PRAGMA integrity_check` sin errores, ninguna clave foránea rota, planes de consulta usando los índices y entre 0 y 15 consultas por página, sin consultas repetidas por fila. `python manage.py limpiar_datos` también actualiza las estadísticas de la base (`PRAGMA optimize` en SQLite, `ANALYZE` en PostgreSQL).

## Seguridad

- Contraseñas con los validadores de Django y bloqueo por 15 minutos tras 5 intentos fallidos por correo o 30 por dirección IP.
- Verificación en dos pasos para todos los usuarios: clientes y equipo ingresan con su contraseña y un código enviado al correo; la administración de datos exige la misma verificación.
- Límites de peticiones en registro, recuperación de contraseña, mensajes, archivos, asistente y API.
- Política de seguridad de contenido (CSP) sin scripts en línea, protección contra incrustación, `Referrer-Policy`, `Permissions-Policy` y páginas privadas sin caché.
- Archivos adjuntos privados: solo los descarga el dueño de la solicitud o el equipo; se validan extensión y tamaño.
- Protección CSRF en todos los formularios y cierre de sesión solo por POST.
- Registro de actividad de accesos al panel, cambios de estado, cotizaciones, asignaciones y exportaciones.
- Tratamiento de datos alineado con la Ley 19.628: aceptación de términos, descarga de datos y eliminación de cuenta.

## Configuración

Las opciones se definen con variables de entorno o en el archivo `.env` de la raíz del proyecto (hay un ejemplo en `.env.example`); una variable de entorno real tiene prioridad sobre el archivo.

| Variable | Uso | Valor por defecto |
|----------|-----|-------------------|
| `DJANGO_DEBUG` | Modo desarrollo (`1`) o producción (`0`) | `1` |
| `DJANGO_SECRET_KEY` | Clave secreta; obligatoria en producción | clave de desarrollo |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos, separados por coma | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes confiables, por ejemplo `https://axztra.cl` | vacío |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` | Conexión a PostgreSQL (normalmente se escriben en `.env`) | `axztra`, `postgres`, vacía, `localhost`, `5432` |
| `DATABASE_URL` | Reemplaza lo anterior con una sola dirección: `postgres://usuario:clave@host:5432/axztra` o `sqlite:///db.sqlite3` para probar sin PostgreSQL | vacío |
| `REDIS_URL` | Caché compartida entre procesos, por ejemplo `redis://localhost:6379/0` | caché en memoria |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Servidor SMTP; si no se define `EMAIL_HOST`, los correos se muestran en la terminal | consola |
| `DEFAULT_FROM_EMAIL` | Remitente de los correos | `AXZTRA <notificaciones@axztra.cl>` |
| `AXZTRA_URL_SITIO` | Dirección pública usada en los enlaces de los correos | `http://127.0.0.1:8000` |
| `DJANGO_SSL_REDIRECT`, `DJANGO_HSTS_SEGUNDOS`, `DJANGO_DETRAS_DE_PROXY` | Opciones HTTPS para producción | desactivadas |
| `DJANGO_ADMIN_URL` | Ruta de la administración de datos | `admin/` |
| `AXZTRA_BOTPRESS_SCRIPTS` | Scripts de un asistente Botpress, separados por coma; reemplazan al asistente propio en las pantallas de solicitud | vacío |
| `AXZTRA_LIMITES_ACTIVOS` | Activa los límites de peticiones | `1` |
| `AXZTRA_VERIFICACION_CLIENTES` | Pide el código de verificación también a los clientes (el equipo siempre lo usa) | `1` |

Los datos de contacto, el número de WhatsApp, el horario y el aviso del sitio se editan desde Panel, Contenido del sitio.

## Despliegue en producción

1. Crear una base PostgreSQL y definir `DATABASE_URL`, `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, el servidor SMTP y, si hay más de un proceso, `REDIS_URL`.
2. Instalar `pip install -r requirements-produccion.txt`.
3. Ejecutar `python manage.py migrate` y `python manage.py collectstatic --noinput`.
4. Crear el administrador con `python manage.py createsuperuser`.
5. Iniciar con Gunicorn en Linux (`gunicorn axztra.wsgi -w 4 -b 0.0.0.0:8000`) o Waitress en Windows (`waitress-serve --port=8000 axztra.wsgi:application`), detrás de un proxy con HTTPS.
6. Revisar la configuración con `python manage.py check --deploy`.
7. Programar `python manage.py limpiar_datos` una vez al día.

WhiteNoise sirve los archivos estáticos si está instalado. Los adjuntos se guardan en la carpeta `media`, que debe respaldarse junto con la base de datos.

## API de integración

Base: `/api/v1/`. Las respuestas son JSON.

| Método y ruta | Autenticación | Descripción |
|---------------|---------------|-------------|
| `GET /api/v1/servicios/` | Pública | Servicios activos; filtro opcional `?tipo=Creacion`. |
| `POST /api/v1/estimaciones/` | Pública, con límite de peticiones | Calcula una estimación con `tipo_sitio`, `complejidad`, `num_paginas`, `funcionalidades` e `integraciones`. |
| `GET /api/v1/solicitudes/` | Token | Solicitudes paginadas; filtros `estado`, `tipo`, `desde` (AAAA-MM-DD), `pagina` y `por_pagina`. |
| `GET /api/v1/solicitudes/<numero>/` | Token | Detalle con historial, estimación y cotización. |

Los tokens se crean con `python manage.py crear_token_api "Facturación"` y se envían en la cabecera `Authorization: Token <valor>`. Solo se almacena su huella SHA-256 y se pueden desactivar desde la administración de datos.

## Comandos

| Comando | Descripción |
|---------|-------------|
| `python manage.py comprobar_base` | Comprueba la conexión con PostgreSQL y explica qué revisar si falla. |
| `python manage.py datos_demo [--reiniciar]` | Crea usuarios, solicitudes y consultas de demostración. |
| `python manage.py crear_token_api <nombre>` | Genera un token para la API. |
| `python manage.py limpiar_datos` | Elimina códigos vencidos, sesiones expiradas y conversaciones antiguas del asistente, y actualiza las estadísticas de la base. |
| `python manage.py generar_carga --clientes 300 --solicitudes 3000` | Genera datos sintéticos para pruebas de volumen. |
| `python manage.py prueba_carga --usuarios 300` | Mide tiempos de respuesta con usuarios simultáneos contra un servidor en ejecución. |

## Pruebas

```
python manage.py test plataforma
```

La suite tiene 104 pruebas: estimación, validaciones, páginas públicas, accesos de navegación, cabeceras de seguridad, cuentas, bloqueo de intentos, verificación en dos pasos, formularios de solicitud, envíos duplicados, adjuntos y permisos, mensajes, panel, cotizaciones, tablero, exportaciones, permisos por rol, API, asistente, modelos, integridad de la base de datos y comandos.

Resultados de la revisión final:

- 104 de 104 pruebas aprobadas.
- 2.000 combinaciones de estimación calculadas en el navegador y en el servidor con resultados idénticos.
- Recorrido automatizado en navegador con 28 comprobaciones: portada, formulario por pasos, asistente, cotización por ítems, tablero, menú móvil, botón Inicio, barra inferior y botón para ver la contraseña.
- Prueba de concurrencia: 300 usuarios simultáneos y 1.500 peticiones sin errores, mediana 1,69 s y P95 1,73 s, en un equipo de un núcleo con 3.009 solicitudes en la base.

## Pendientes conocidos

- El proyecto se probó con Django 5.0. Esa versión ya no recibe parches de seguridad, por lo que antes de publicar conviene actualizar a Django 5.2 LTS y volver a ejecutar las pruebas.
- El asistente funciona con reglas propias. Para un modelo de lenguaje o Botpress basta con definir `AXZTRA_BOTPRESS_SCRIPTS` o reemplazar el método `AsistenteVirtual.responder`.
- Pagos en línea y facturación electrónica quedan fuera del alcance, como indica el informe; la API permite integrarlos.
- La interfaz está solo en español.
- Los textos legales son una base y deben ser revisados por un abogado antes de operar.
- PostgreSQL: el código se revisó y las pruebas se ejecutaron con SQLite, porque el entorno de desarrollo no tenía un servidor PostgreSQL; la primera ejecución real en PostgreSQL es la de tu equipo. Si algo falla, `python manage.py comprobar_base` indica qué revisar. Redis, Gunicorn y Waitress tampoco se probaron en un servidor real.
