(function () {
    'use strict';

    function obtenerCookie(nombre) {
        var partes = document.cookie ? document.cookie.split(';') : [];
        for (var i = 0; i < partes.length; i++) {
            var par = partes[i].trim();
            if (par.indexOf(nombre + '=') === 0) {
                return decodeURIComponent(par.substring(nombre.length + 1));
            }
        }
        return '';
    }

    function tokenCsrf() {
        var campo = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return campo ? campo.value : obtenerCookie('csrftoken');
    }

    function iniciarMensajes() {
        var avisos = document.querySelectorAll('.flash');
        avisos.forEach(function (aviso) {
            var cerrar = function () {
                aviso.classList.add('saliendo');
                setTimeout(function () { aviso.remove(); }, 300);
            };
            var boton = aviso.querySelector('.cerrar');
            if (boton) { boton.addEventListener('click', cerrar); }
            if (!aviso.classList.contains('flash-danger')) {
                setTimeout(cerrar, 6000);
            }
        });
    }

    function iniciarConfirmaciones() {
        document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
            form.addEventListener('submit', function (e) {
                if (!window.confirm(form.getAttribute('data-confirmar'))) {
                    e.preventDefault();
                }
            });
        });
    }

    function iniciarSitioActual() {
        var opciones = document.querySelectorAll('input[name="tiene_sitio_actual"]');
        var bloque = document.getElementById('bloque-url-actual');
        if (!opciones.length || !bloque) { return; }
        var actualizar = function () {
            var marcada = document.querySelector('input[name="tiene_sitio_actual"]:checked');
            bloque.hidden = !(marcada && marcada.value === 'si');
        };
        opciones.forEach(function (op) { op.addEventListener('change', actualizar); });
        actualizar();
    }

    function mensajeValidacion(campo) {
        var v = campo.validity;
        if (v.valueMissing) { return 'Completa este campo.'; }
        if (v.rangeUnderflow) { return 'El valor mínimo es ' + campo.min + '.'; }
        if (v.rangeOverflow) { return 'El valor máximo es ' + campo.max + '.'; }
        if (v.badInput || v.stepMismatch) { return 'Ingresa un número entero.'; }
        if (v.tooLong) { return 'El texto es demasiado largo.'; }
        if (v.typeMismatch) { return 'Revisa el formato de este campo.'; }
        return campo.validationMessage;
    }

    function iniciarAsistenteFormulario() {
        var form = document.getElementById('form-asistente');
        if (!form) { return; }
        form.classList.remove('sin-js');

        var pasos = form.querySelectorAll('.paso-form');
        var marcadores = document.querySelectorAll('.pasos-lateral li[data-paso]');
        var total = pasos.length;
        var actual = parseInt(form.getAttribute('data-paso-inicial') || '1', 10);

        var mostrar = function (numero) {
            actual = Math.max(1, Math.min(total, numero));
            pasos.forEach(function (paso) {
                paso.classList.toggle('visible', parseInt(paso.getAttribute('data-paso'), 10) === actual);
            });
            marcadores.forEach(function (li) {
                var n = parseInt(li.getAttribute('data-paso'), 10);
                li.classList.remove('hecho', 'actual', 'pendiente');
                if (n < actual) { li.classList.add('hecho'); }
                else if (n === actual) { li.classList.add('actual'); }
                else { li.classList.add('pendiente'); }
                var estado = li.querySelector('small');
                if (estado) {
                    estado.textContent = n < actual ? 'Completado' : (n === actual ? 'En curso' : 'Pendiente');
                }
            });
            window.scrollTo({ top: 0, behavior: 'smooth' });
        };

        var validarPaso = function (numero) {
            var paso = form.querySelector('.paso-form[data-paso="' + numero + '"]');
            var valido = true;
            paso.querySelectorAll('[data-error-js]').forEach(function (e) { e.remove(); });

            paso.querySelectorAll('input, select, textarea').forEach(function (campo) {
                if (campo.type === 'checkbox' || campo.type === 'radio' || campo.type === 'hidden') { return; }
                if (campo.closest('[hidden]')) { return; }
                if (!campo.checkValidity()) {
                    valido = false;
                    campo.classList.add('is-invalid');
                    var msg = document.createElement('div');
                    msg.className = 'error-campo';
                    msg.setAttribute('data-error-js', '1');
                    msg.textContent = mensajeValidacion(campo);
                    campo.insertAdjacentElement('afterend', msg);
                } else {
                    campo.classList.remove('is-invalid');
                }
            });

            paso.querySelectorAll('[data-requiere-seleccion]').forEach(function (grupo) {
                if (!grupo.querySelector('input:checked')) {
                    valido = false;
                    var msg = document.createElement('div');
                    msg.className = 'error-campo';
                    msg.setAttribute('data-error-js', '1');
                    msg.textContent = grupo.getAttribute('data-requiere-seleccion');
                    grupo.insertAdjacentElement('afterend', msg);
                }
            });

            var urlBloque = paso.querySelector('#bloque-url-actual');
            if (urlBloque && !urlBloque.hidden) {
                var url = urlBloque.querySelector('input');
                if (url && !url.value.trim()) {
                    valido = false;
                    url.classList.add('is-invalid');
                    var aviso = document.createElement('div');
                    aviso.className = 'error-campo';
                    aviso.setAttribute('data-error-js', '1');
                    aviso.textContent = 'Indica la dirección de tu sitio actual.';
                    url.insertAdjacentElement('afterend', aviso);
                }
            }

            if (!valido) {
                var primero = paso.querySelector('.is-invalid, [data-error-js]');
                if (primero) { primero.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
            }
            return valido;
        };

        form.querySelectorAll('[data-siguiente]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (validarPaso(actual)) { mostrar(actual + 1); }
            });
        });

        form.querySelectorAll('[data-anterior]').forEach(function (btn) {
            btn.addEventListener('click', function () { mostrar(actual - 1); });
        });

        form.addEventListener('submit', function (e) {
            for (var n = 1; n <= total; n++) {
                if (!validarPaso(n)) {
                    e.preventDefault();
                    mostrar(n);
                    validarPaso(n);
                    return;
                }
            }
        });

        form.addEventListener('input', function (e) {
            if (e.target.classList.contains('is-invalid') && e.target.checkValidity()) {
                e.target.classList.remove('is-invalid');
                var siguiente = e.target.nextElementSibling;
                if (siguiente && siguiente.hasAttribute('data-error-js')) { siguiente.remove(); }
            }
        });

        form.addEventListener('change', function (e) {
            if (e.target.type === 'checkbox' || e.target.type === 'radio') {
                var grupo = e.target.closest('[data-requiere-seleccion]');
                if (grupo && grupo.nextElementSibling && grupo.nextElementSibling.hasAttribute('data-error-js')) {
                    grupo.nextElementSibling.remove();
                }
            }
        });

        mostrar(actual);
    }

    function iniciarChat() {
        var boton = document.getElementById('burbuja-boton');
        var ventana = document.getElementById('chat-ventana');
        if (!boton || !ventana) { return; }

        var lista = ventana.querySelector('.chat-mensajes');
        var sugerencias = ventana.querySelector('.chat-sugerencias');
        var form = ventana.querySelector('.chat-form');
        var entrada = form.querySelector('input[type="text"]');
        var enviar = form.querySelector('button');
        var cerrar = ventana.querySelector('[data-cerrar-chat]');
        var invitacion = document.getElementById('burbuja-invitacion');
        var urlMensaje = ventana.getAttribute('data-url-mensaje');
        var urlHistorial = ventana.getAttribute('data-url-historial');
        var cargado = false;
        var ocupado = false;

        var agregar = function (texto, esAsistente, acciones) {
            var burbuja = document.createElement('div');
            burbuja.className = 'chat-msg ' + (esAsistente ? 'bot' : 'usuario');
            burbuja.textContent = texto;
            if (acciones && acciones.length) {
                var caja = document.createElement('div');
                caja.className = 'chat-acciones';
                acciones.forEach(function (accion) {
                    var enlace = document.createElement('a');
                    enlace.href = accion.url;
                    enlace.textContent = accion.texto;
                    caja.appendChild(enlace);
                });
                burbuja.appendChild(caja);
            }
            lista.appendChild(burbuja);
            if (esAsistente && burbuja.offsetHeight > lista.clientHeight * 0.6) {
                lista.scrollTop = burbuja.offsetTop - lista.offsetTop - 12;
            } else {
                lista.scrollTop = lista.scrollHeight;
            }
        };

        var mostrarSugerencias = function (items) {
            sugerencias.innerHTML = '';
            (items || []).forEach(function (texto) {
                var b = document.createElement('button');
                b.type = 'button';
                b.textContent = texto;
                b.addEventListener('click', function () { mandar(texto); });
                sugerencias.appendChild(b);
            });
        };

        var escribiendo = function (activo) {
            var existente = lista.querySelector('.chat-escribiendo');
            if (activo && !existente) {
                var el = document.createElement('div');
                el.className = 'chat-escribiendo';
                el.innerHTML = '<span></span><span></span><span></span>';
                lista.appendChild(el);
                lista.scrollTop = lista.scrollHeight;
            } else if (!activo && existente) {
                existente.remove();
            }
        };

        var mandar = function (texto) {
            texto = (texto || '').trim();
            if (!texto || ocupado) { return; }
            ocupado = true;
            enviar.disabled = true;
            agregar(texto, false);
            mostrarSugerencias([]);
            entrada.value = '';
            escribiendo(true);

            fetch(urlMensaje, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': tokenCsrf() },
                body: JSON.stringify({ mensaje: texto })
            })
                .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, datos: d }; }); })
                .then(function (res) {
                    escribiendo(false);
                    if (!res.ok) {
                        agregar(res.datos.error || 'No pude procesar tu mensaje. Intenta nuevamente.', true);
                        return;
                    }
                    agregar(res.datos.respuesta, true, res.datos.acciones);
                    mostrarSugerencias(res.datos.sugerencias);
                })
                .catch(function () {
                    escribiendo(false);
                    agregar('No hay conexión con el servidor. Revisa tu internet e intenta de nuevo.', true);
                })
                .then(function () {
                    ocupado = false;
                    enviar.disabled = false;
                    entrada.focus();
                });
        };

        var cargarHistorial = function () {
            if (cargado) { return; }
            cargado = true;
            var saludoContexto = ventana.getAttribute('data-saludo');
            fetch(urlHistorial, { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (datos) {
                    if (datos.mensajes && datos.mensajes.length) {
                        datos.mensajes.forEach(function (m) { agregar(m.texto, m.es_asistente); });
                        if (saludoContexto) { agregar(saludoContexto, true); }
                    } else {
                        agregar(saludoContexto || datos.saludo, true);
                    }
                    mostrarSugerencias(datos.sugerencias);
                })
                .catch(function () {
                    agregar(saludoContexto || 'Hola, soy el asistente de AXZTRA. ¿En qué te puedo ayudar?', true);
                });
        };

        var abrir = function () {
            ventana.hidden = false;
            boton.setAttribute('aria-expanded', 'true');
            if (invitacion) { invitacion.remove(); invitacion = null; }
            cargarHistorial();
            setTimeout(function () { entrada.focus(); }, 50);
        };

        var ocultar = function () {
            ventana.hidden = true;
            boton.setAttribute('aria-expanded', 'false');
            boton.focus();
        };

        boton.addEventListener('click', function () {
            if (ventana.hidden) { abrir(); } else { ocultar(); }
        });
        cerrar.addEventListener('click', ocultar);
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && !ventana.hidden) { ocultar(); }
        });
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            mandar(entrada.value);
        });

        document.querySelectorAll('[data-abrir-asistente]').forEach(function (el) {
            el.addEventListener('click', function (e) {
                e.preventDefault();
                abrir();
            });
        });

        if (invitacion) {
            var cerrarInv = invitacion.querySelector('.cerrar');
            if (cerrarInv) {
                cerrarInv.addEventListener('click', function () { invitacion.remove(); invitacion = null; });
            }
            invitacion.addEventListener('click', function (e) {
                if (!e.target.closest('.cerrar')) { abrir(); }
            });
        }
    }

    function iniciarContactoWhatsapp() {
        var form = document.getElementById('form-contacto');
        if (!form) { return; }
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var nombre = form.querySelector('[name="nombre"]').value.trim();
            var servicio = form.querySelector('[name="servicio"]');
            var mensaje = form.querySelector('[name="mensaje"]').value.trim();
            var texto = 'Hola, soy ' + nombre + '. Me interesa: ' + servicio.options[servicio.selectedIndex].text + '.';
            if (mensaje) { texto += ' ' + mensaje; }
            window.open('https://wa.me/' + form.getAttribute('data-whatsapp') + '?text=' + encodeURIComponent(texto), '_blank', 'noopener');
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarMensajes();
        iniciarConfirmaciones();
        iniciarSitioActual();
        iniciarAsistenteFormulario();
        iniciarChat();
        iniciarContactoWhatsapp();
    });
})();
