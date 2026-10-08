// AXZTRA: estimación y formulario por pasos.
//
// Calcula la estimación referencial en el navegador con la misma fórmula de estimacion.py (sección 3.5 del informe).
// Se usa en la portada (CU02) y en el formulario de cuatro pasos para crear una página web (CU09, DA-02).

(function () {
    'use strict';

    var AXZTRA = window.AXZTRA = window.AXZTRA || {};

    // Porcentaje del total redondeado a múltiplos de $10.000.
    function redondear(total, porcentaje) {
        return Math.floor((total * porcentaje + 50 * 10000) / (100 * 10000)) * 10000;
    }

    // Fórmula: precio base + páginas extra + funcionalidades + integraciones (por el factor de diseño).
    AXZTRA.calcularEstimacion = function (cfg, sel) {
        var factor = cfg.factores[sel.complejidad] || cfg.factores.media;
        var paginas = parseInt(sel.paginas, 10);
        if (!isFinite(paginas)) { paginas = 1; }
        paginas = Math.max(1, Math.min(paginas, cfg.maximoPaginas));
        var funcionalidades = (sel.funcionalidades || []).filter(function (c, i, a) { return cfg.funcionalidades[c] && a.indexOf(c) === i; });
        var integraciones = (sel.integraciones || []).filter(function (c, i, a) { return cfg.integraciones[c] && a.indexOf(c) === i; });
        var lineas = [];
        var base = cfg.bases[sel.tipo] || cfg.bases.corporativo;
        lineas.push({ concepto: 'Precio base del tipo de sitio', monto: base });
        var extra = Math.max(0, paginas - cfg.paginasIncluidas);
        if (extra) {
            lineas.push({ concepto: extra === 1 ? '1 página adicional' : extra + ' páginas adicionales', monto: Math.trunc(extra * cfg.costoPagina * factor) });
        }
        funcionalidades.forEach(function (c) {
            lineas.push({ concepto: cfg.funcionalidades[c].nombre, monto: Math.trunc(cfg.funcionalidades[c].precio * factor) });
        });
        integraciones.forEach(function (c) {
            lineas.push({ concepto: cfg.integraciones[c].nombre, monto: Math.trunc(cfg.integraciones[c].precio * factor) });
        });
        var total = lineas.reduce(function (s, l) { return s + l.monto; }, 0);
        var semanas = (cfg.semanas[sel.complejidad] || cfg.semanas.media).slice();
        if (funcionalidades.indexOf('tienda') !== -1 || integraciones.indexOf('pagos') !== -1) {
            semanas[0] += 1;
            semanas[1] += 1;
        }
        if (paginas > 15) { semanas[1] += 1; }
        return {
            total: total,
            minimo: redondear(total, 90),
            maximo: redondear(total, 115),
            semanasMin: semanas[0],
            semanasMax: semanas[1],
            lineas: lineas
        };
    };

    // Texto del rango, por ejemplo "$320.000 a $400.000".
    function textoRango(minimo, maximo) {
        return AXZTRA.clp(minimo) + ' a ' + AXZTRA.clp(maximo);
    }

    // Muestra el rango con una animación de números.
    function mostrarRango(elemento, minimo, maximo, desdeCero) {
        var objetivo = elemento._objetivo;
        if (objetivo && objetivo.minimo === minimo && objetivo.maximo === maximo) {
            if (!elemento._cancelar) { elemento.textContent = textoRango(minimo, maximo); }
            return;
        }
        elemento._objetivo = { minimo: minimo, maximo: maximo };
        if (elemento._cancelar) {
            elemento._cancelar();
            elemento._cancelar = null;
        }
        var inicio = elemento._mostrado;
        if (!inicio) {
            if (!desdeCero) {
                elemento._mostrado = { minimo: minimo, maximo: maximo };
                elemento.textContent = textoRango(minimo, maximo);
                return;
            }
            inicio = { minimo: 0, maximo: 0 };
        }
        elemento._mostrado = inicio;
        elemento.classList.remove('cambio');
        void elemento.offsetWidth;
        elemento.classList.add('cambio');
        var cancelar = AXZTRA.interpolar(inicio.maximo === 0 ? 1000 : 450, function (avance) {
            if (avance >= 1) {
                elemento._mostrado = { minimo: minimo, maximo: maximo };
                elemento._cancelar = null;
                elemento.textContent = textoRango(minimo, maximo);
                return;
            }
            var a = inicio.minimo + (minimo - inicio.minimo) * avance;
            var b = inicio.maximo + (maximo - inicio.maximo) * avance;
            elemento._mostrado = { minimo: a, maximo: b };
            elemento.textContent = textoRango(Math.round(a / 1000) * 1000, Math.round(b / 1000) * 1000);
        });
        if (elemento._mostrado.minimo !== minimo || elemento._mostrado.maximo !== maximo) {
            elemento._cancelar = cancelar;
        }
    }

    // Lee los precios que entrega el servidor (configuracion_publica en estimacion.py).
    function leerConfig(id) {
        var nodo = document.getElementById(id);
        return nodo ? JSON.parse(nodo.textContent) : null;
    }

    // Valores marcados de un grupo de casillas.
    function marcados(raiz, nombre) {
        return Array.prototype.map.call(raiz.querySelectorAll('input[name="' + nombre + '"]:checked'), function (i) { return i.value; });
    }

    // Valor elegido de un grupo de opciones.
    function valorRadio(raiz, nombre, defecto) {
        var marcado = raiz.querySelector('input[name="' + nombre + '"]:checked');
        return marcado ? marcado.value : defecto;
    }

    // Estimador de la portada (CU02).
    function iniciarPortada() {
        var raiz = document.getElementById('estimador-portada');
        var cfg = leerConfig('config-estimacion');
        if (!raiz || !cfg) { return; }
        var monto = raiz.querySelector('[data-monto]');
        var plazo = raiz.querySelector('[data-plazo]');
        var paginas = raiz.querySelector('input[name="num_paginas"]');
        var salidaPaginas = raiz.querySelector('output');
        var continuar = raiz.querySelector('[data-continuar]');

        var actualizar = function () {
            var sel = {
                tipo: valorRadio(raiz, 'tipo_sitio', 'corporativo'),
                complejidad: valorRadio(raiz, 'complejidad', 'media'),
                paginas: paginas.value,
                funcionalidades: marcados(raiz, 'funcionalidades'),
                integraciones: []
            };
            var r = AXZTRA.calcularEstimacion(cfg, sel);
            salidaPaginas.textContent = paginas.value;
            mostrarRango(monto, r.minimo, r.maximo, true);
            plazo.textContent = r.semanasMin + ' a ' + r.semanasMax + ' semanas';
            var parametros = new URLSearchParams();
            parametros.append('tipo_sitio', sel.tipo);
            parametros.append('complejidad', sel.complejidad);
            parametros.append('num_paginas', sel.paginas);
            sel.funcionalidades.forEach(function (f) { parametros.append('funcionalidades', f); });
            var destino = continuar.getAttribute('data-destino') + '?' + parametros.toString();
            if (continuar.hasAttribute('data-registro')) {
                continuar.href = continuar.getAttribute('data-registro') + '?next=' + encodeURIComponent(destino);
            } else {
                continuar.href = destino;
            }
        };
        raiz.addEventListener('input', actualizar);
        raiz.addEventListener('change', actualizar);
        actualizar();
    }

    // Resumen lateral del formulario que se actualiza con cada respuesta.
    function iniciarResumenVivo(form, cfg) {
        var panel = document.getElementById('resumen-vivo');
        if (!panel || !cfg) { return function () {}; }
        var monto = panel.querySelector('[data-monto]');
        var plazo = panel.querySelector('[data-plazo]');
        var lista = panel.querySelector('ul');
        return function () {
            var sel = {
                tipo: valorRadio(form, 'tipo_sitio', 'corporativo'),
                complejidad: valorRadio(form, 'complejidad', 'media'),
                paginas: (form.querySelector('input[name="num_paginas"]') || {}).value || 5,
                funcionalidades: marcados(form, 'funcionalidades'),
                integraciones: marcados(form, 'integraciones')
            };
            var r = AXZTRA.calcularEstimacion(cfg, sel);
            mostrarRango(monto, r.minimo, r.maximo, false);
            plazo.textContent = r.semanasMin + ' a ' + r.semanasMax + ' semanas';
            lista.textContent = '';
            r.lineas.forEach(function (l) {
                var li = document.createElement('li');
                var a = document.createElement('span');
                var b = document.createElement('span');
                a.textContent = l.concepto;
                b.textContent = AXZTRA.clp(l.monto);
                li.appendChild(a);
                li.appendChild(b);
                lista.appendChild(li);
            });
        };
    }

    // Botón "Sugerir funcionalidades" del paso 3: pide sugerencias al servidor según el rubro.
    function iniciarSugerencias(form) {
        var caja = document.getElementById('sugerencias-asistente');
        if (!caja) { return; }
        var boton = caja.querySelector('[data-pedir]');
        var resultado = caja.querySelector('[data-resultado]');
        var aplicar = caja.querySelector('[data-aplicar]');
        var ultimas = null;

        boton.addEventListener('click', function () {
            var descripcion = (form.querySelector('[name="descripcion_negocio"]') || {}).value || '';
            var rubro = (form.querySelector('[name="rubro"]') || {}).value || '';
            boton.setAttribute('aria-disabled', 'true');
            resultado.textContent = 'Analizando la información de tu negocio...';
            AXZTRA.postJSON(caja.getAttribute('data-url'), {
                descripcion: descripcion,
                rubro: rubro,
                objetivos: marcados(form, 'objetivos')
            }).then(function (r) {
                boton.removeAttribute('aria-disabled');
                if (!r.ok) {
                    resultado.textContent = r.datos.error || 'No pude generar sugerencias en este momento.';
                    return;
                }
                ultimas = r.datos;
                resultado.textContent = '';
                var items = r.datos.funcionalidades.concat(r.datos.integraciones);
                if (!items.length) {
                    resultado.textContent = 'Cuéntame un poco más sobre tu negocio en el paso anterior para sugerirte funcionalidades.';
                    aplicar.hidden = true;
                    return;
                }
                if (r.datos.ideas) {
                    var p = document.createElement('p');
                    p.className = 'pequeno texto-2 sin-margen';
                    p.textContent = 'Para tu rubro suele funcionar bien incluir ' + r.datos.ideas + '.';
                    resultado.appendChild(p);
                }
                var ul = document.createElement('ul');
                items.forEach(function (item) {
                    var li = document.createElement('li');
                    var fuerte = document.createElement('strong');
                    fuerte.textContent = item.nombre + ': ';
                    li.appendChild(fuerte);
                    li.appendChild(document.createTextNode(item.motivo));
                    ul.appendChild(li);
                });
                resultado.appendChild(ul);
                aplicar.hidden = false;
            }).catch(function () {
                boton.removeAttribute('aria-disabled');
                resultado.textContent = 'No hay conexión con el servidor. Intenta nuevamente.';
            });
        });

        aplicar.addEventListener('click', function () {
            if (!ultimas) { return; }
            var marcar = function (nombre, clave) {
                var input = form.querySelector('input[name="' + nombre + '"][value="' + clave + '"]');
                if (input && !input.checked) {
                    input.checked = true;
                    var opcion = input.closest('.opcion');
                    if (opcion) { opcion.classList.add('sugerida'); }
                }
            };
            ultimas.funcionalidades.forEach(function (i) { marcar('funcionalidades', i.clave); });
            ultimas.integraciones.forEach(function (i) { marcar('integraciones', i.clave); });
            form.dispatchEvent(new Event('change', { bubbles: true }));
            aplicar.hidden = true;
            AXZTRA.avisar('Marcamos las funcionalidades sugeridas. Puedes quitar las que no necesites.', 'success');
        });
    }

    // Cambio entre los cuatro pasos: valida cada paso antes de avanzar.
    function iniciarFormularioPasos() {
        var form = document.getElementById('form-pasos');
        if (!form) { return; }
        form.classList.remove('sin-js');
        var cfg = leerConfig('config-estimacion');
        var pasos = form.querySelectorAll('.paso-formulario');
        var marcadores = document.querySelectorAll('.pasos li[data-paso]');
        var total = pasos.length;
        var actual = parseInt(form.getAttribute('data-paso-inicial') || '1', 10);
        var actualizarResumen = iniciarResumenVivo(form, cfg);

        var mostrar = function (numero, desplazar) {
            form.setAttribute('data-direccion', numero < actual ? 'atras' : 'adelante');
            actual = Math.max(1, Math.min(total, numero));
            pasos.forEach(function (paso) {
                var visible = parseInt(paso.getAttribute('data-paso'), 10) === actual;
                paso.classList.toggle('visible', visible);
                paso.setAttribute('aria-hidden', visible ? 'false' : 'true');
            });
            marcadores.forEach(function (li) {
                var n = parseInt(li.getAttribute('data-paso'), 10);
                li.classList.remove('hecho', 'actual', 'pendiente');
                li.classList.add(n < actual ? 'hecho' : (n === actual ? 'actual' : 'pendiente'));
                var estado = li.querySelector('small');
                if (estado) { estado.textContent = n < actual ? 'Completado' : (n === actual ? 'En curso' : 'Pendiente'); }
                var bola = li.querySelector('.bola');
                if (bola) {
                    bola.textContent = '';
                    if (n < actual) {
                        var marca = document.createElement('i');
                        marca.className = 'fa-solid fa-check';
                        marca.setAttribute('aria-hidden', 'true');
                        bola.appendChild(marca);
                    } else {
                        bola.textContent = String(n);
                    }
                }
            });
            if (desplazar) {
                form.scrollIntoView({ behavior: 'smooth', block: 'start' });
                var titulo = form.querySelector('.paso-formulario.visible h2');
                if (titulo) { titulo.setAttribute('tabindex', '-1'); titulo.focus({ preventScroll: true }); }
            }
        };

        var validarPaso = function (n) {
            return AXZTRA.validar(form.querySelector('.paso-formulario[data-paso="' + n + '"]'));
        };

        form.querySelectorAll('[data-siguiente]').forEach(function (b) {
            b.addEventListener('click', function () { if (validarPaso(actual)) { mostrar(actual + 1, true); } });
        });
        form.querySelectorAll('[data-anterior]').forEach(function (b) {
            b.addEventListener('click', function () { mostrar(actual - 1, true); });
        });
        form.addEventListener('submit', function (e) {
            for (var n = 1; n <= total; n++) {
                if (!validarPaso(n)) {
                    e.preventDefault();
                    mostrar(n, false);
                    validarPaso(n);
                    return;
                }
            }
        });
        form.addEventListener('input', actualizarResumen);
        form.addEventListener('change', actualizarResumen);
        iniciarSugerencias(form);
        mostrar(actual, false);
        actualizarResumen();
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarPortada();
        iniciarFormularioPasos();
    });
})();
