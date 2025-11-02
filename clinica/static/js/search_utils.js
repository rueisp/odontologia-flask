// static/js/search_utils.js

// Función para inicializar la búsqueda de pacientes con sugerencias
// Recibe:
// - searchInput: El elemento <input> donde el usuario escribe
// - suggestionsContainer: El <div> donde se mostrarán las sugerencias
// - hiddenPatientIdInput: El elemento <input type="hidden"> donde se guarda el ID del paciente seleccionado
// - onPatientSelectedCallback: Función a llamar cuando un paciente es seleccionado (recibe patientData).
//                              Debe actualizar la UI con los datos del paciente.
// - onSearchClearedCallback: Función a llamar cuando el campo de búsqueda se vacía completamente o se limpia el paciente.
//                              Debe resetear la UI a un estado sin paciente seleccionado.
export function initializePatientSearch(searchInput, suggestionsContainer, hiddenPatientIdInput, onPatientSelectedCallback, onSearchClearedCallback) {
    let searchTimeout;
    let lastSelectedPatientId = null; // Para saber si el input ha sido modificado después de una selección

    // Listener para el input de búsqueda
    searchInput.addEventListener('input', async () => {
        clearTimeout(searchTimeout);
        const query = searchInput.value.trim();

        // Si el usuario borra el contenido del input de búsqueda
        if (query.length === 0) {
            suggestionsContainer.innerHTML = '';
            suggestionsContainer.classList.add('hidden');
            hiddenPatientIdInput.value = ''; // Limpiar el ID oculto
            lastSelectedPatientId = null; // Resetear el control de selección
            if (onSearchClearedCallback) {
                onSearchClearedCallback(); // Llamar callback de limpieza
            }
            return;
        }

        // Si el usuario empieza a escribir después de haber seleccionado un paciente (y el query es diferente al nombre seleccionado)
        if (lastSelectedPatientId !== null && query !== searchInput.dataset.lastSelectedName) {
             hiddenPatientIdInput.value = ''; // Limpiar el ID oculto
             lastSelectedPatientId = null; // Resetear el control de selección
             if (onSearchClearedCallback) { // Notificar que el paciente seleccionado se ha "deseleccionado"
                 onSearchClearedCallback();
             }
        }
        
        if (query.length < 2) {
            suggestionsContainer.innerHTML = '';
            suggestionsContainer.classList.add('hidden');
            return;
        }

        searchTimeout = setTimeout(async () => {
            try {
                // Asumiendo que esta es tu ruta AJAX para sugerencias
                const response = await fetch(`/pacientes/buscar_sugerencias_ajax?q=${encodeURIComponent(query)}`);
                const data = await response.json();
                suggestionsContainer.innerHTML = '';

                if (data.length > 0) {
                    data.forEach(paciente => {
                        const item = document.createElement('div');
                        item.className = 'px-4 py-2 cursor-pointer hover:bg-gray-100 rounded-md text-sm';
                        item.textContent = `${paciente.nombre} (ID: ${paciente.id})`;
                        item.dataset.patientId = paciente.id;
                        item.addEventListener('click', async () => {
                            searchInput.value = paciente.nombre; // Rellenar el input visible
                            hiddenPatientIdInput.value = paciente.id; // Guardar el ID oculto
                            lastSelectedPatientId = paciente.id; // Marcar como seleccionado
                            searchInput.dataset.lastSelectedName = paciente.nombre; // Guardar el nombre para futuras comparaciones
                            suggestionsContainer.classList.add('hidden');

                            // Cargar detalles completos del paciente y pasar al callback
                            try {
                                const infoResponse = await fetch(`/pacientes/obtener_paciente_ajax/${paciente.id}`);
                                const patientData = await infoResponse.json();
                                if (onPatientSelectedCallback) {
                                    onPatientSelectedCallback(patientData);
                                }
                            } catch (error) {
                                console.error('Error al obtener datos del paciente seleccionado:', error);
                                // Opcional: limpiar y notificar al usuario
                                hiddenPatientIdInput.value = '';
                                lastSelectedPatientId = null;
                                if (onSearchClearedCallback) onSearchClearedCallback();
                            }
                        });
                        suggestionsContainer.appendChild(item);
                    });
                    suggestionsContainer.classList.remove('hidden');
                } else {
                    suggestionsContainer.classList.add('hidden');
                    // Si no hay sugerencias, y el ID oculto está vacío, el usuario podría estar creando uno nuevo
                    // Llama al callback de limpieza si no hay selección
                    if (!hiddenPatientIdInput.value && onSearchClearedCallback) {
                        onSearchClearedCallback();
                    }
                }
            } catch (error) {
                console.error('Error al buscar sugerencias:', error);
                suggestionsContainer.classList.add('hidden');
                // En caso de error, llama al callback de limpieza
                if (onSearchClearedCallback) {
                    onSearchClearedCallback();
                }
            }
        }, 300); // Debounce
    });

    // Ocultar sugerencias al hacer clic fuera
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !suggestionsContainer.contains(e.target)) {
            suggestionsContainer.classList.add('hidden');
        }
    });
}

// Función para precargar un paciente si ya hay un ID en el hiddenInput al inicio
export async function preloadPatient(patientId, searchInput, hiddenPatientIdInput, onPatientSelectedCallback) {
    if (patientId) {
        try {
            const infoResponse = await fetch(`/pacientes/obtener_paciente_ajax/${patientId}`);
            if (!infoResponse.ok) {
                throw new Error('No se pudieron precargar los datos del paciente.');
            }
            const patientData = await infoResponse.json();
            searchInput.value = patientData.nombre; // Rellenar el input visible
            hiddenPatientIdInput.value = patientId; // Asegurar que el ID oculto esté seteado
            // Guarda el nombre seleccionado para que la lógica de 'input' no lo limpie inmediatamente
            searchInput.dataset.lastSelectedName = patientData.nombre; 
            
            if (onPatientSelectedCallback) {
                onPatientSelectedCallback(patientData);
            }
            return patientData; // Devuelve los datos del paciente precargado
        } catch (error) {
            console.error('Error al precargar datos del paciente:', error);
            // Si falla la precarga, limpiar y resetear
            searchInput.value = '';
            hiddenPatientIdInput.value = '';
            searchInput.dataset.lastSelectedName = ''; // Limpiar el nombre seleccionado
            if (onPatientSelectedCallback) onPatientSelectedCallback(null); // Notificar que no se pudo cargar
            return null;
        }
    }
    return null;
}