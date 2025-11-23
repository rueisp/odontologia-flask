// static/js/index.js

// Importar las funciones de búsqueda y precarga desde el módulo de utilidades
import { initializePatientSearch, preloadPatient } from './search_utils.js';

document.addEventListener('DOMContentLoaded', () => {
    // Definimos la variable de estado al principio, accesible para todas las funciones dentro del DOMContentLoaded
    let pacienteSeleccionado = null;

    // ==================================================================
    // SECCIÓN: BÚSQUEDA DE PACIENTES Y PANEL DERECHO
    // ==================================================================
    const inputBusqueda = document.getElementById('busquedaPaciente');
    const contenedorSugerencias = document.getElementById('sugerencias');

    // --- Referencias a los botones y su contenedor ---
    const panelControles = document.getElementById('panel-controles');
    const btnEditarPacienteEl = document.getElementById('btnEditarPaciente');
    const btnVerCitasHistorialEl = document.getElementById('btnVerCitas');

    // Elementos del DOM en el panel derecho (cabecera)
    const nombrePacienteHeader = document.getElementById('nombrePaciente');
    const documentoPacienteHeader = document.getElementById('documentoPaciente');
    const telefonoPacienteHeader = document.getElementById('telefonoPaciente');

    // Elementos del DOM en el panel derecho (sección "Datos")
    const estadoPacienteSpan = document.getElementById('estadoPaciente');
    const generoEdadSpan = document.getElementById('generoEdad');
    const fechaNacimientoSpan = document.getElementById('fechaNacimiento');
    const direccionPacienteSpan = document.getElementById('direccionPaciente');
    const emailPacienteSpan = document.getElementById('emailPaciente');
    const ocupacionPacienteSpan = document.getElementById('ocupacionPaciente');
    const aseguradoraPacienteSpan = document.getElementById('aseguradoraPaciente');
    const alergiasPacienteSpan = document.getElementById('alergiasPaciente');
    const enfermedadPacienteSpan = document.getElementById('enfermedadPaciente');

    // Elementos del DOM en el panel derecho (sección "Citas")
    const ultimaCitaSpan = document.getElementById('ultimaCita');
    const proximaCitaPanelDerechoSpan = document.getElementById('proximaCitaPanelDerecho');
    const motivoFrecuenteSpan = document.getElementById('motivoFrecuente');

    // Elementos del DOM en el panel derecho (sección "Imágenes")
    const dentigramaDisplayContainer = document.getElementById('dentigramaDisplayContainer');
    const dentigramaDisplay = document.getElementById('dentigramaDisplay');
    const noDentigrama = document.getElementById('noDentigrama');

    const imagen1DisplayContainer = document.getElementById('imagen1DisplayContainer');
    const imagen1Display = document.getElementById('imagen1Display');
    const noImagen1 = document.getElementById('noImagen1');

    const imagen2DisplayContainer = document.getElementById('imagen2DisplayContainer');
    const imagen2Display = document.getElementById('imagen2Display');
    const noImagen2 = document.getElementById('noImagen2');

    // --- Funciones auxiliares para mostrar/ocultar imágenes ---
    function displayImage(container, imgElement, noImgElement, imageUrl) {
        if (!container || !imgElement || !noImgElement) {
            console.warn('displayImage: Elementos no encontrados');
            return;
        }

        if (imageUrl && imageUrl.trim() !== '') {
            imgElement.src = imageUrl;
            imgElement.onerror = function() {
                console.error(`Error al cargar imagen: ${imageUrl}`);
                hideImage(container, imgElement, noImgElement);
            };
            container.classList.remove('hidden');
            imgElement.classList.remove('hidden');
            noImgElement.classList.add('hidden');
        } else {
            hideImage(container, imgElement, noImgElement);
        }
    }

    function hideImage(container, imgElement, noImgElement) {
        if (!container || !imgElement || !noImgElement) return;
        
        container.classList.add('hidden');
        imgElement.src = '';
        imgElement.classList.add('hidden');
        noImgElement.classList.remove('hidden');
    }

    // Función para limpiar o resetear el panel derecho
    function clearRightPanel() {
        const setText = (element, text) => {
            if (element) element.textContent = text;
        };

        setText(nombrePacienteHeader, 'No especificado');
        setText(documentoPacienteHeader, 'No especificado');
        setText(telefonoPacienteHeader, 'No especificado');

        // Sección "Datos"
        setText(estadoPacienteSpan, 'No especificado');
        setText(generoEdadSpan, 'N/A • No especificada');
        setText(fechaNacimientoSpan, 'No especificado');
        setText(direccionPacienteSpan, 'No especificado');
        setText(emailPacienteSpan, 'No especificado');
        setText(ocupacionPacienteSpan, 'No especificado');
        setText(aseguradoraPacienteSpan, 'No especificado');
        setText(alergiasPacienteSpan, 'No especificado');
        setText(enfermedadPacienteSpan, 'No especificado');

        // Sección "Citas"
        setText(ultimaCitaSpan, 'No hay citas anteriores registradas');
        setText(proximaCitaPanelDerechoSpan, 'No tiene próximas citas');
        setText(motivoFrecuenteSpan, 'No especificado');

        // Sección "Imágenes"
        hideImage(dentigramaDisplayContainer, dentigramaDisplay, noDentigrama);
        hideImage(imagen1DisplayContainer, imagen1Display, noImagen1);
        hideImage(imagen2DisplayContainer, imagen2Display, noImagen2);

        if (panelControles) panelControles.style.display = 'none';
        pacienteSeleccionado = null;
        if (inputBusqueda) inputBusqueda.value = '';
    }


    // Función para actualizar el panel derecho con los datos del paciente
    function actualizarPanelDerechoConPaciente(datos) {
        if (!datos) {
            clearRightPanel();
            return;
        }

        pacienteSeleccionado = datos;

        const setText = (id_element, value, defaultValue = 'No especificado') => {
            const el = document.getElementById(id_element);
            if (el) el.textContent = value || defaultValue;
        };

        setText('nombrePaciente', datos.nombre);
        const edadDisplay = datos.edad === 'No especificada' ? 'No especificada' : `${datos.edad} años`;
        setText('generoEdad', `${datos.genero || 'N/A'} • ${edadDisplay}`);
        setText('fechaNacimiento', datos.fecha_nacimiento);
        setText('estadoPaciente', datos.estado);
        setText('documentoPaciente', datos.documento);
        setText('telefonoPaciente', datos.telefono);
        setText('direccionPaciente', datos.direccion);
        setText('emailPaciente', datos.email);
        setText('ocupacionPaciente', datos.ocupacion);
        setText('aseguradoraPaciente', datos.aseguradora);
        setText('alergiasPaciente', datos.alergias);
        setText('enfermedadPaciente', datos.enfermedad_actual);

        setText('ultimaCita', datos.ultima_cita_info);
        setText('proximaCitaPanelDerecho', datos.proxima_cita_paciente_info);
        setText('motivoFrecuente', datos.motivo_frecuente_info);

        displayImage(dentigramaDisplayContainer, dentigramaDisplay, noDentigrama, datos.dentigrama_url);
        displayImage(imagen1DisplayContainer, imagen1Display, noImagen1, datos.imagen_1);
        displayImage(imagen2DisplayContainer, imagen2Display, noImagen2, datos.imagen_2);

        if (panelControles) {
            panelControles.style.display = 'flex';

            const editUrlBase = panelControles.dataset.editUrlBase;
            const citasUrlBase = panelControles.dataset.citasUrlBase;

            if (btnEditarPacienteEl) {
                btnEditarPacienteEl.onclick = function () {
                    if (pacienteSeleccionado && pacienteSeleccionado.id) {
                        window.location.href = editUrlBase.replace('0', pacienteSeleccionado.id);
                    } else {
                        alert('Por favor, selecciona un paciente válido.');
                    }
                };
            }

            if (btnVerCitasHistorialEl) {
                btnVerCitasHistorialEl.onclick = function () {
                    if (pacienteSeleccionado && pacienteSeleccionado.id) {
                        window.location.href = citasUrlBase.replace('0', pacienteSeleccionado.id);
                    } else {
                        alert('Por favor, selecciona un paciente válido.');
                    }
                };
            }
        }

        mostrarSeccion('datos');
    }

    // Variable para el input temporal (MOVIDA FUERA DEL BLOQUE IF)
    let tempHiddenPatientIdInput = null;

    // --- Inicialización de la búsqueda de pacientes para el dashboard ---
    if (inputBusqueda && contenedorSugerencias) {
        tempHiddenPatientIdInput = document.createElement('input');
        tempHiddenPatientIdInput.type = 'hidden';
        tempHiddenPatientIdInput.id = 'temp_dashboard_patient_id';

        initializePatientSearch(inputBusqueda, contenedorSugerencias, tempHiddenPatientIdInput,
            actualizarPanelDerechoConPaciente, clearRightPanel);
    }

    // Al cargar la página, limpia el panel derecho
    clearRightPanel();

    // --- Lógica para el cambio de pestañas en el panel derecho ---
    const tabButtons = document.querySelectorAll('.tab-btn-panel-derecho');
    const sections = {
        'datos': document.getElementById('seccion-datos'),
        'citas': document.getElementById('seccion-citas'),
        'imagenes': document.getElementById('seccion-imagenes')
    };

    function mostrarSeccion(seccionIdActiva) {
        const idsSeccionesPanelDerecho = ['datos', 'citas', 'imagenes'];

        idsSeccionesPanelDerecho.forEach(idPanel => {
            const el = document.getElementById(`seccion-${idPanel}`);
            if (el) el.classList.add('hidden');
        });

        const seccionActivaEl = document.getElementById(`seccion-${seccionIdActiva}`);
        if (seccionActivaEl) seccionActivaEl.classList.remove('hidden');

        // Actualizar estilo de los botones de pestañas del panel DERECHO
        document.querySelectorAll('.tab-btn-panel-derecho').forEach(btn => {
            btn.classList.remove('border-black', 'text-black', 'font-semibold');
            btn.classList.add('text-gray-600', 'border-transparent');
        });

        // Activar el botón correspondiente a la sección activa
        const btnActiva = document.querySelector(`.tab-btn-panel-derecho[data-seccion="${seccionIdActiva}"]`);
        if (btnActiva) {
            btnActiva.classList.add('border-black', 'text-black', 'font-semibold');
            btnActiva.classList.remove('text-gray-600', 'border-transparent');
        }
    }

    // Añadir event listeners a los botones de pestañas del panel derecho
    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const seccion = this.dataset.seccion;
            if (seccion) {
                mostrarSeccion(seccion);
            }
        });
    });

    // Llamada inicial para mostrar la sección de 'datos' en el panel derecho
    const primerTabPanelDerecho = document.querySelector('.tab-btn-panel-derecho[data-seccion="datos"]');
    if (primerTabPanelDerecho) mostrarSeccion('datos');


    // --- Lógica principal al cargar la página: Cargar paciente por defecto si el ID está presente ---
    if (typeof DEFAULT_PATIENT_ID !== 'undefined' && DEFAULT_PATIENT_ID !== null && tempHiddenPatientIdInput) {
        preloadPatient(DEFAULT_PATIENT_ID, inputBusqueda, tempHiddenPatientIdInput, actualizarPanelDerechoConPaciente)
            .catch(error => {
                console.error('Error al cargar paciente por defecto en dashboard:', error);
                clearRightPanel();
            });
    }

    // ==================================================================
    // SECCIÓN: CITAS DE HOY (PANEL CENTRAL) - MANEJO DE ESTADOS Y FILTROS
    // ==================================================================
    const listaCitasContainer = document.getElementById('lista-citas-hoy');
    const noAppointmentsMessageCitasHoy = document.querySelector(".no-appointments-message");

    if (listaCitasContainer) {
        listaCitasContainer.addEventListener('click', function (event) {
            const botonCambiarEstado = event.target.closest('.btn-cambiar-estado');
            if (botonCambiarEstado) {
                event.preventDefault();
                const tarjetaCita = botonCambiarEstado.closest('.appointment-card');
                if (!tarjetaCita) return;

                const citaId = tarjetaCita.dataset.citaId;
                const nuevoEstado = botonCambiarEstado.dataset.nuevoEstado;
                const estadoActual = tarjetaCita.dataset.estado;

                if (estadoActual === nuevoEstado) return;

                // Crear un AbortController para timeout
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos timeout

                fetch(`/calendario/cita/actualizar_estado/${citaId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ estado: nuevoEstado }),
                    signal: controller.signal
                })
                    .then(response => {
                        clearTimeout(timeoutId);
                        if (!response.ok) {
                            return response.json().then(err => { 
                                throw new Error(err.message || `Error del servidor: ${response.status}`) 
                            }).catch(() => {
                                throw new Error(`Error del servidor: ${response.status}`);
                            });
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            tarjetaCita.dataset.estado = data.nuevo_estado;
                            const estadoSpan = tarjetaCita.querySelector('.cita-estado-badge');
                            if (estadoSpan) {
                                estadoSpan.textContent = data.nuevo_estado.charAt(0).toUpperCase() + data.nuevo_estado.slice(1);
                                estadoSpan.className = 'cita-estado-badge text-xs px-2 py-0.5 rounded-full mt-1 inline-block';
                                if (data.nuevo_estado === 'completada') estadoSpan.classList.add('bg-green-100', 'text-green-700');
                                else if (data.nuevo_estado === 'cancelada') estadoSpan.classList.add('bg-red-100', 'text-red-700');
                                else estadoSpan.classList.add('bg-yellow-100', 'text-yellow-700');
                            }

                            const accionesDiv = tarjetaCita.querySelector('.appointment-actions');
                            if (accionesDiv) {
                                accionesDiv.querySelectorAll('.btn-cambiar-estado').forEach(btn => {
                                    btn.style.display = 'inline-block';
                                    if (data.nuevo_estado === 'completada' && btn.dataset.nuevoEstado !== 'completada' && btn.dataset.nuevoEstado !== 'cancelada') {
                                        btn.style.display = 'none';
                                    } else if (data.nuevo_estado === 'cancelada' && btn.dataset.nuevoEstado !== 'cancelada') {
                                        btn.style.display = 'none';
                                    } else if (btn.dataset.nuevoEstado === data.nuevo_estado) {
                                        btn.style.display = 'none';
                                    }
                                });
                            }

                            actualizarContadoresPestañasCitasHoy();

                            const filtroActivo = document.querySelector('.tab-appointment-filter[data-active="true"]');
                            if (filtroActivo && filtroActivo.dataset.status !== 'todas' && filtroActivo.dataset.status !== data.nuevo_estado) {
                                tarjetaCita.style.display = 'none';
                                // Recalcular contadores después de ocultar
                                const todasLasTarjetas = document.querySelectorAll(".appointment-card");
                                const visibles = Array.from(todasLasTarjetas).filter(card => card.style.display !== 'none').length;
                                verificarMensajeNoCitas(filtroActivo.dataset.status, visibles, todasLasTarjetas.length);
                            }
                        } else { 
                            alert("Error al actualizar: " + (data.message || 'Error desconocido')); 
                        }
                    })
                    .catch(error => {
                        clearTimeout(timeoutId);
                        console.error('Error en fetch:', error);
                        if (error.name === 'AbortError') {
                            alert('La solicitud tardó demasiado. Por favor, verifica tu conexión e intenta nuevamente.');
                        } else {
                            alert('Error al actualizar cita: ' + error.message);
                        }
                    });
            }
        });
    }

    function actualizarContadoresPestañasCitasHoy() {
        const setTextContent = (id, count) => {
            const el = document.getElementById(id);
            if (el) el.textContent = count;
        };
        setTextContent('count-todas', document.querySelectorAll('.appointment-card[data-estado]').length);
        setTextContent('count-pendientes', document.querySelectorAll('.appointment-card[data-estado="pendiente"]').length);
        setTextContent('count-completadas', document.querySelectorAll('.appointment-card[data-estado="completada"]').length);
        setTextContent('count-canceladas', document.querySelectorAll('.appointment-card[data-estado="cancelada"]').length);
    }

    const tabsCitasHoy = document.querySelectorAll(".tab-appointment-filter");

    tabsCitasHoy.forEach(tab => {
        tab.addEventListener("click", () => {
            tabsCitasHoy.forEach(t => t.dataset.active = "false");
            tab.dataset.active = "true";
            const statusToShow = tab.dataset.status;
            filtrarTarjetasCita(statusToShow);
        });
    });

    function filtrarTarjetasCita(statusToShow) {
        const todasLasTarjetasCitas = document.querySelectorAll(".appointment-card");
        let visibleCount = 0;
        todasLasTarjetasCitas.forEach(card => {
            const cardStatus = card.dataset.estado;
            if (statusToShow === 'todas' || cardStatus === statusToShow) {
                card.style.display = '';
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        verificarMensajeNoCitas(statusToShow, visibleCount, todasLasTarjetasCitas.length);
    }

    function verificarMensajeNoCitas(statusMostrando, conteoVisible, conteoTotal) {
        if (!noAppointmentsMessageCitasHoy) return;

        if (conteoVisible === 0) {
            noAppointmentsMessageCitasHoy.style.display = '';
            const textoMensajeP = noAppointmentsMessageCitasHoy.querySelector('p');
            if (textoMensajeP) {
                let texto = `No hay citas ${statusMostrando === 'todas' ? 'programadas' : statusMostrando} para hoy.`;
                if (statusMostrando !== 'todas' && conteoTotal > 0) {
                    texto = `No hay citas que coincidan con el filtro '${statusMostrando}'.`;
                } else if (statusMostrando === 'todas' && conteoTotal === 0) {
                    texto = 'No hay citas programadas para hoy.';
                }
                textoMensajeP.textContent = texto;
            }
        } else {
            noAppointmentsMessageCitasHoy.style.display = 'none';
        }
    }

    const todasLasTarjetasIniciales = document.querySelectorAll(".appointment-card");
    if (listaCitasContainer && todasLasTarjetasIniciales.length > 0) {
        actualizarContadoresPestañasCitasHoy();
        const tabTodas = document.querySelector('.tab-appointment-filter[data-status="todas"]');
        if (tabTodas) {
            tabTodas.dataset.active = "true";
            filtrarTarjetasCita("todas");
        }
    } else if (noAppointmentsMessageCitasHoy) {
        noAppointmentsMessageCitasHoy.style.display = '';
        const textoMensajeP = noAppointmentsMessageCitasHoy.querySelector('p');
        if (textoMensajeP) textoMensajeP.textContent = 'No hay citas programadas para hoy.';
        actualizarContadoresPestañasCitasHoy();
    }
});