// AXZTRA: funciones del panel del equipo.
//
// Cotización por ítems con cálculo de IVA (CU16) y tablero para mover solicitudes entre etapas (CU17).

(function () {
    'use strict';

    var AXZTRA = window.AXZTRA = window.AXZTRA || {};

    // Ítems de la cotización: agrega y quita filas y recalcula neto, IVA y total.
    function iniciarItems() {
        var tabla = document.getElementById('items-cotizacion');
        if (!tabla) { return; }
        var cuerpo = tabla.querySelector('tbody');
        var plantilla = document.getElementById('plantilla-item');
        var totalFormularios = document.getElementById('id_items-TOTAL_FORMS');
        var agregar = document.querySelector('[data-agregar-item]');
        var iva = parseFloat(tabla.getAttribute('data-iva') || '19');
        var salidaNeto = document.querySelector('[data-neto]');
        var salidaIva = document.querySelector('[data-iva-monto]');
        var salidaTotal = document.querySelector('[data-total]');

        var recalcular = function () {
            var neto = 0;
            cuerpo.querySelectorAll('tr').forEach(function (fila) {
                var quitar = fila.querySelector('input[name$="-DELETE"]');
                var cantidad = parseInt((fila.querySelector('input[name$="-cantidad"]') || {}).value, 10) || 0;
                var precio = parseInt((fila.querySelector('input[name$="-precio_unitario"]') || {}).value, 10) || 0;
                var subtotal = cantidad * precio;
                var celda = fila.querySelector('[data-subtotal]');
                if (celda) { celda.textContent = AXZTRA.clp(subtotal); }
                fila.style.opacity = quitar && quitar.checked ? '0.45' : '';
                if (!(quitar && quitar.checked)) { neto += subtotal; }
            });
            var montoIva = Math.round(neto * iva / 100);
            salidaNeto.textContent = AXZTRA.clp(neto);
            salidaIva.textContent = AXZTRA.clp(montoIva);
            salidaTotal.textContent = AXZTRA.clp(neto + montoIva);
        };

        if (agregar && plantilla && totalFormularios) {
            agregar.addEventListener('click', function () {
                var indice = parseInt(totalFormularios.value, 10);
                var html = plantilla.innerHTML.replace(/__prefix__/g, String(indice));
                var temporal = document.createElement('tbody');
                temporal.innerHTML = html.trim();
                var fila = temporal.firstElementChild;
                cuerpo.appendChild(fila);
                totalFormularios.value = String(indice + 1);
                var primero = fila.querySelector('input[name$="-descripcion"]');
                if (primero) { primero.focus(); }
                recalcular();
            });
        }
        tabla.addEventListener('input', recalcular);
        tabla.addEventListener('change', recalcular);
        recalcular();
    }

    // Tablero: al soltar una tarjeta en otra columna cambia el estado en el servidor.
    function iniciarTablero() {
        var tablero = document.getElementById('tablero');
        if (!tablero) { return; }
        var arrastrada = null;
        var origen = null;

        var actualizarContadores = function () {
            tablero.querySelectorAll('.columna-tablero').forEach(function (col) {
                var contador = col.querySelector('[data-cantidad]');
                var total = parseInt(contador.getAttribute('data-total'), 10);
                var visibles = col.querySelectorAll('.tarjeta-tablero').length;
                contador.textContent = String(Math.max(total, visibles));
            });
        };

        tablero.addEventListener('dragstart', function (e) {
            var tarjeta = e.target.closest('.tarjeta-tablero');
            if (!tarjeta) { return; }
            arrastrada = tarjeta;
            origen = tarjeta.parentElement;
            tarjeta.classList.add('arrastrando');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', tarjeta.getAttribute('data-id'));
        });

        tablero.addEventListener('dragend', function () {
            if (arrastrada) { arrastrada.classList.remove('arrastrando'); }
            tablero.querySelectorAll('.columna-tablero.sobre').forEach(function (c) { c.classList.remove('sobre'); });
        });

        tablero.addEventListener('dragover', function (e) {
            var columna = e.target.closest('.columna-tablero');
            if (!columna || !arrastrada) { return; }
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            tablero.querySelectorAll('.columna-tablero.sobre').forEach(function (c) { if (c !== columna) { c.classList.remove('sobre'); } });
            columna.classList.add('sobre');
        });

        tablero.addEventListener('drop', function (e) {
            var columna = e.target.closest('.columna-tablero');
            if (!columna || !arrastrada) { return; }
            e.preventDefault();
            columna.classList.remove('sobre');
            var lista = columna.querySelector('.lista');
            if (lista === origen) { return; }
            var tarjeta = arrastrada;
            var anterior = origen;
            var totalOrigen = anterior.closest('.columna-tablero').querySelector('[data-cantidad]');
            var totalDestino = columna.querySelector('[data-cantidad]');
            lista.prepend(tarjeta);
            AXZTRA.postJSON(tarjeta.getAttribute('data-url'), { estado: columna.getAttribute('data-estado') })
                .then(function (r) {
                    if (!r.ok) {
                        anterior.prepend(tarjeta);
                        AXZTRA.avisar(r.datos.error || 'No se pudo cambiar el estado.', 'danger');
                        return;
                    }
                    totalOrigen.setAttribute('data-total', String(Math.max(0, parseInt(totalOrigen.getAttribute('data-total'), 10) - 1)));
                    totalDestino.setAttribute('data-total', String(parseInt(totalDestino.getAttribute('data-total'), 10) + 1));
                    actualizarContadores();
                    tarjeta.classList.remove('recien-movida');
                    void tarjeta.offsetWidth;
                    tarjeta.classList.add('recien-movida');
                    tarjeta.addEventListener('animationend', function quitar() {
                        tarjeta.classList.remove('recien-movida');
                        tarjeta.removeEventListener('animationend', quitar);
                    });
                    AXZTRA.avisar(tarjeta.getAttribute('data-numero') + ' pasó a ' + r.datos.nombre + '.', 'success');
                })
                .catch(function () {
                    anterior.prepend(tarjeta);
                    AXZTRA.avisar('No hay conexión con el servidor. Intenta nuevamente.', 'danger');
                });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarItems();
        iniciarTablero();
    });
})();
