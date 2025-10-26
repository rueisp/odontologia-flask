// index.js

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
    const estadoPacienteSpan = document.getElementById('estadoPaciente'); // Se usará para estado_civil
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
        if (imageUrl) {
            imgElement.src = imageUrl;
            container.classList.remove('hidden');
            imgElement.classList.remove('hidden');
            noImgElement.classList.add('hidden');
        } else {
            hideImage(container, imgElement, noImgElement);
        }
    }

    function hideImage(container, imgElement, noImgElement) {
        container.classList.add('hidden');
        imgElement.src = ''; // Limpia la fuente
        imgElement.classList.add('hidden');
        noImgElement.classList.remove('hidden');
    }

    // Función para limpiar o resetear el panel derecho (AHORA TAMBIÉN LIMPIA EL INPUT DE BÚSQUEDA)
    function clearRightPanel() {
        nombrePacienteHeader.textContent = 'No especificado';
        documentoPacienteHeader.textContent = 'No especificado';
        telefonoPacienteHeader.textContent = 'No especificado';

        // Sección "Datos"
        estadoPacienteSpan.textContent = 'No especificado';
        generoEdadSpan.textContent = 'N/A • No especificada';
        fechaNacimientoSpan.textContent = 'No especificado';
        direccionPacienteSpan.textContent = 'No especificado';
        emailPacienteSpan.textContent = 'No especificado';
        ocupacionPacienteSpan.textContent = 'No especificado';
        aseguradoraPacienteSpan.textContent = 'No especificado';
        alergiasPacienteSpan.textContent = 'No especificado';
        enfermedadPacienteSpan.textContent = 'No especificado';

        // Sección "Citas"
        ultimaCitaSpan.textContent = 'No hay citas anteriores registradas';
        proximaCitaPanelDerechoSpan.textContent = 'No tiene próximas citas';
        motivoFrecuenteSpan.textContent = 'No especificado';

        // Sección "Imágenes"
        hideImage(dentigramaDisplayContainer, dentigramaDisplay, noDentigrama);
        hideImage(imagen1DisplayContainer, imagen1Display, noImagen1);
        hideImage(imagen2DisplayContainer, imagen2Display, noImagen2);
        
        panelControles.style.display = 'none'; // Oculta los botones de acción
        pacienteSeleccionado = null; // Reinicia el paciente seleccionado
        inputBusqueda.value = ''; // <--- NUEVO: Limpia el campo de búsqueda
    }

    // Al cargar la página, limpia el panel derecho
    clearRightPanel();


    // --- Lógica de la Búsqueda ---
    if (inputBusqueda && contenedorSugerencias) {
        inputBusqueda.addEventListener('input', async () => {
            const query = inputBusqueda.value.trim();
            if (query.length < 2) { // Buena práctica: buscar a partir de 2 caracteres
                contenedorSugerencias.innerHTML = '';
                contenedorSugerencias.classList.add('hidden');
                if (query.length === 0) { // Si el campo de búsqueda se vacía, limpia el panel derecho
                    clearRightPanel();
                }
                return;
            }
            try {
                // La URL aquí está bien: /pacientes/buscar_sugerencias_ajax
                const response = await fetch(`/pacientes/buscar_sugerencias_ajax?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                contenedorSugerencias.innerHTML = '';
                if (!data.length) {
                    contenedorSugerencias.classList.add('hidden');
                    return;
                }
                data.forEach(paciente => {
                    const item = document.createElement('div');
                    item.className = 'px-4 py-2 cursor-pointer hover:bg-gray-100 rounded-xl transition-colors text-sm'; // Añadido text-sm
                    item.textContent = `${paciente.nombre} (ID: ${paciente.id})`; // Muestra también el ID para identificar mejor
                    item.dataset.patientId = paciente.id; // Almacena el ID del paciente
                    item.addEventListener('click', async () => {
                        // No actualizamos inputBusqueda.value aquí, lo hará actualizarPanelDerechoConPaciente
                        contenedorSugerencias.classList.add('hidden');
                        try {
                            const infoResponse = await fetch(`/pacientes/obtener_paciente_ajax/${paciente.id}`);
                            const datosPaciente = await infoResponse.json();
                            
                            pacienteSeleccionado = datosPaciente; 
                            actualizarPanelDerechoConPaciente(datosPaciente);
                            
                        } catch (error) {
                            console.error('Error al obtener datos del paciente:', error);
                            // Opcional: mostrar un mensaje de error al usuario
                        }
                    });
                    contenedorSugerencias.appendChild(item);
                });
                contenedorSugerencias.classList.remove('hidden');
            } catch (error) {
                console.error('Error al buscar sugerencias:', error);
            }
        });

        document.addEventListener('click', (e) => {
            if (!contenedorSugerencias.contains(e.target) && e.target !== inputBusqueda) {
                contenedorSugerencias.classList.add('hidden');
            }
        });
    }

    if (btnEditarPacienteEl && panelControles) {
        btnEditarPacienteEl.addEventListener('click', () => {
            if (pacienteSeleccionado && pacienteSeleccionado.id) {
                const urlBase = panelControles.dataset.editUrlBase;
                const urlFinal = urlBase.replace('/0/', `/${pacienteSeleccionado.id}/`);
                window.location.href = urlFinal;
            } else {
                alert('Por favor, busca y selecciona un paciente primero.');
            }
        });
    }

    if (btnVerCitasHistorialEl && panelControles) {
        btnVerCitasHistorialEl.addEventListener('click', () => {
            if (pacienteSeleccionado && pacienteSeleccionado.id) {
                const urlBase = panelControles.dataset.citasUrlBase;
                const urlFinal = urlBase.replace('/0/', `/${pacienteSeleccionado.id}/`);
                window.location.href = urlFinal;
            } else {
                alert('Por favor, busca y selecciona un paciente primero.');
            }
        });
    }

    // Función para actualizar el panel derecho
    function actualizarPanelDerechoConPaciente(datos) {
        // Rellenar el input de búsqueda
        inputBusqueda.value = datos.nombre; // <--- NUEVO: Rellena el input de búsqueda

        const setText = (id_element, value, defaultValue = 'No especificado') => {
            const el = document.getElementById(id_element);
            if (el) el.textContent = value || defaultValue;
        };

        setText('nombrePaciente', datos.nombre);
        // Ajuste para el display de edad si viene como string "No especificada"
        const edadDisplay = datos.edad === 'No especificada' ? 'No especificada' : `${datos.edad} años`;
        setText('generoEdad', `${datos.genero || 'N/A'} • ${edadDisplay}`);
        setText('fechaNacimiento', datos.fecha_nacimiento);
        setText('estadoPaciente', datos.estado); // 'estado' aquí es el del paciente, ej. estado_civil
        setText('documentoPaciente', datos.documento);
        setText('telefonoPaciente', datos.telefono);
        setText('direccionPaciente', datos.direccion);
        setText('emailPaciente', datos.email);
        setText('ocupacionPaciente', datos.ocupacion);
        setText('aseguradoraPaciente', datos.aseguradora);
        setText('alergiasPaciente', datos.alergias);
        setText('enfermedadPaciente', datos.enfermedad_actual);

        // Actualizar información de citas específicas del paciente en el panel derecho
        setText('ultimaCita', datos.ultima_cita_info);
        setText('proximaCitaPanelDerecho', datos.proxima_cita_paciente_info);
        setText('motivoFrecuente', datos.motivo_frecuente_info);

        // Actualizar sección de imágenes utilizando las funciones auxiliares y los contenedores del HTML
        displayImage(dentigramaDisplayContainer, dentigramaDisplay, noDentigrama, datos.dentigrama_url);
        displayImage(imagen1DisplayContainer, imagen1Display, noImagen1, datos.imagen_1);
        displayImage(imagen2DisplayContainer, imagen2Display, noImagen2, datos.imagen_2);

        // Mostrar los botones de acción
        panelControles.style.display = 'flex';

        // Asegurarse de que la pestaña "Datos" esté activa y visible al cargar un paciente
        mostrarSeccion('datos');
    }

    // ==================================================================
    // SECCIÓN: CITAS DE HOY (PANEL CENTRAL) - MANEJO DE ESTADOS Y FILTROS
    // ==================================================================
    const listaCitasContainer = document.getElementById('lista-citas-hoy');

    if (listaCitasContainer) {
        listaCitasContainer.addEventListener('click', function(event) {
            const botonCambiarEstado = event.target.closest('.btn-cambiar-estado');
            if (botonCambiarEstado) {
                event.preventDefault();
                const tarjetaCita = botonCambiarEstado.closest('.appointment-card');
                const citaId = tarjetaCita.dataset.citaId;
                const nuevoEstado = botonCambiarEstado.dataset.nuevoEstado;
                const estadoActual = tarjetaCita.dataset.estado;

                if (estadoActual === nuevoEstado) return;
                
                fetch(`/calendario/cita/actualizar_estado/${citaId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' /*, 'X-CSRFToken': TU_CSRF_TOKEN */ },
                    body: JSON.stringify({ estado: nuevoEstado })
                })
                .then(response => {
                    if (!response.ok) return response.json().then(err => { throw new Error(err.message || `Error: ${response.status}`) });
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        tarjetaCita.dataset.estado = data.nuevo_estado;
                        const estadoSpan = tarjetaCita.querySelector('.cita-estado-badge'); // Usar una clase específica
                        if (estadoSpan) {
                            estadoSpan.textContent = data.nuevo_estado.charAt(0).toUpperCase() + data.nuevo_estado.slice(1);
                            estadoSpan.className = 'cita-estado-badge text-xs px-2 py-0.5 rounded-full mt-1 inline-block'; // Reset base
                            if (data.nuevo_estado === 'completada') estadoSpan.classList.add('bg-green-100', 'text-green-700');
                            else if (data.nuevo_estado === 'cancelada') estadoSpan.classList.add('bg-red-100', 'text-red-700');
                            else estadoSpan.classList.add('bg-yellow-100', 'text-yellow-700');
                        }

                        const accionesDiv = tarjetaCita.querySelector('.appointment-actions');
                        if (accionesDiv) {
                            // Ocultar botones si el nuevo estado es completada o cancelada, o si ya es el estado actual
                            accionesDiv.querySelectorAll('.btn-cambiar-estado').forEach(btn => {
                                btn.style.display = 'inline-block'; // Mostrar todos por defecto
                                if (data.nuevo_estado === 'completada' && btn.dataset.nuevoEstado !== 'completada' && btn.dataset.nuevoEstado !== 'cancelada') {
                                    btn.style.display = 'none'; // Ocultar si está completada, excepto cancelar
                                } else if (data.nuevo_estado === 'cancelada' && btn.dataset.nuevoEstado !== 'cancelada') {
                                    btn.style.display = 'none'; // Ocultar si está cancelada
                                } else if (btn.dataset.nuevoEstado === data.nuevo_estado) {
                                     btn.style.display = 'none'; // Ocultar el botón si ya es el estado actual
                                }
                            });
                        }
                        
                        actualizarContadoresPestañasCitasHoy();

                        const filtroActivo = document.querySelector('.tab-appointment-filter[data-active="true"]');
                        if (filtroActivo && filtroActivo.dataset.status !== 'todas' && filtroActivo.dataset.status !== data.nuevo_estado) {
                            tarjetaCita.style.display = 'none';
                            verificarMensajeNoCitas(filtroActivo.dataset.status);
                        }
                    } else { alert("Error al actualizar: " + data.message); }
                })
                .catch(error => {
                    console.error('Error en fetch:', error);
                    alert('Error de red al actualizar cita: ' + error.message);
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
    // Asumo que tu HTML tiene un contenedor con la clase 'no-appointments-message' para esto.
    // Si el mensaje está dentro del 'lista-citas-hoy' directamente, el selector debería ser diferente.
    const noAppointmentsMessageCitasHoy = document.querySelector(".no-appointments-message"); 

    tabsCitasHoy.forEach(tab => {
        tab.addEventListener("click", () => {
            tabsCitasHoy.forEach(t => t.dataset.active = "false");
            tab.dataset.active = "true";
            const statusToShow = tab.dataset.status;
            filtrarTarjetasCita(statusToShow);
        });
    });
    
    function filtrarTarjetasCita(statusToShow) {
        const todasLasTarjetasCitas = document.querySelectorAll(".appointment-card"); // Obtener siempre la lista actual
        let visibleCount = 0;
        todasLasTarjetasCitas.forEach(card => {
            const cardStatus = card.dataset.estado;
            if (statusToShow === 'todas' || cardStatus === statusToShow) {
                card.style.display = ''; // O tu display por defecto para las tarjetas
                visibleCount++;
            } else {
                card.style.display = 'none';
            }
        });
        verificarMensajeNoCitas(statusToShow, visibleCount, todasLasTarjetasCitas.length);
    }
    
    function verificarMensajeNoCitas(statusMostrando, conteoVisible, conteoTotal) {
        if (noAppointmentsMessageCitasHoy) {
            if (conteoVisible === 0) {
                noAppointmentsMessageCitasHoy.style.display = ''; // o 'block'
                const textoMensajeP = noAppointmentsMessageCitasHoy.querySelector('p');
                if (textoMensajeP) {
                    let texto = `No hay citas ${statusMostrando === 'todas' ? 'programadas' : statusMostrando} para hoy.`;
                    if (statusMostrando !== 'todas' && conteoTotal > 0) { // Si hay citas en total pero ninguna coincide con el filtro
                        texto = `No hay citas que coincidan con el filtro '${statusMostrando}'.`;
                    } else if (statusMostrando === 'todas' && conteoTotal === 0) { // No hay citas en absoluto
                        texto = 'No hay citas programadas para hoy.';
                    }
                    textoMensajeP.textContent = texto;
                }
            } else {
                noAppointmentsMessageCitasHoy.style.display = 'none';
            }
        }
    }

    // Llamada inicial
    const todasLasTarjetasIniciales = document.querySelectorAll(".appointment-card");
    if (listaCitasContainer && todasLasTarjetasIniciales.length > 0) { 
        actualizarContadoresPestañasCitasHoy();
        const tabTodas = document.querySelector('.tab-appointment-filter[data-status="todas"]');
        if (tabTodas) {
            tabTodas.dataset.active = "true"; // Asegurar que "todas" esté activo
            filtrarTarjetasCita("todas");
        }
    } else if (noAppointmentsMessageCitasHoy) {
        noAppointmentsMessageCitasHoy.style.display = '';
        const textoMensajeP = noAppointmentsMessageCitasHoy.querySelector('p');
        if (textoMensajeP) textoMensajeP.textContent = 'No hay citas programadas para hoy.';
        actualizarContadoresPestañasCitasHoy(); 
    }

    // ==================================================================
    // SECCIÓN: PESTAÑAS DEL PANEL DERECHO (TU FUNCIÓN mostrarSeccion)
    // ==================================================================
    function mostrarSeccion(seccionIdActiva) {
        // IDs de las secciones del panel derecho que se pueden mostrar/ocultar
        const idsSeccionesPanelDerecho = ['datos', 'citas', 'imagenes']; // Asegúrate que estos IDs correspondan a los 'seccion-id'
        
        idsSeccionesPanelDerecho.forEach(idPanel => {
            const el = document.getElementById(`seccion-${idPanel}`);
            if (el) el.classList.add('hidden');
        });

        const seccionActivaEl = document.getElementById(`seccion-${seccionIdActiva}`);
        if (seccionActivaEl) seccionActivaEl.classList.remove('hidden');

        // Actualizar estilo de los botones de pestañas del panel DERECHO
        document.querySelectorAll('.tab-btn-panel-derecho').forEach(btn => {
            btn.classList.remove('border-black', 'text-black', 'font-semibold'); // Quitar estado activo
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
    document.querySelectorAll('.tab-btn-panel-derecho').forEach(btn => {
        btn.addEventListener('click', function() {
            const seccion = this.dataset.seccion; // ej. data-seccion="datos"
            if (seccion) {
                mostrarSeccion(seccion);
            }
        });
    });
    
    // Llamada inicial para mostrar la sección de 'datos' en el panel derecho si no hay paciente seleccionado,
    // o si `mostrarSeccion('datos')` no se llamó antes de que los listeners se adjunten.
    // Esto se mantiene, pero la lógica de DEFAULT_PATIENT_ID lo sobrescribirá si hay un ID en la URL.
    if (!pacienteSeleccionado) { 
       const primerTabPanelDerecho = document.querySelector('.tab-btn-panel-derecho[data-seccion="datos"]');
       if(primerTabPanelDerecho) mostrarSeccion('datos'); 
    }


    // --- NUEVA LÓGICA PRINCIPAL AL CARGAR LA PÁGINA: Cargar paciente por defecto si el ID está presente ---
    // La variable DEFAULT_PATIENT_ID se define en index.html a través de Jinja2
    if (typeof DEFAULT_PATIENT_ID !== 'undefined' && DEFAULT_PATIENT_ID !== null) {
        // Hacemos la llamada AJAX para obtener los detalles del paciente
        fetch(`/pacientes/obtener_paciente_ajax/${DEFAULT_PATIENT_ID}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                pacienteSeleccionado = data; // Almacenamos los datos en la variable de estado
                actualizarPanelDerechoConPaciente(data); // Rellenamos el panel derecho y el input de búsqueda
            })
            .catch(error => {
                console.error('Error al cargar paciente por defecto:', error);
                clearRightPanel(); // Limpiamos el panel si falla la carga
                // Puedes mostrar un mensaje al usuario si la carga del paciente por defecto falla
            });
    }


}); // Cierre del DOMContentLoaded principal