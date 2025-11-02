// Archivo: clinica/static/js/editor_dentigrama.js
// VERSIÓN UNIFICADA Y CORREGIDA PARA FONDO CSS, SUBIDA A CLOUDINARY Y GROSOR DE TRAZOS.
// ¡ESTRUCTURA DE LISTENERS CORREGIDA Y EXPOSICIÓN DE LA INICIALIZACIÓN GLOBAL!

// --- Variables Globales (DECLARADAS UNA SOLA VEZ AL PRINCIPIO DEL ARCHIVO) ---
let dentigramaCanvas;
let ctx;
let dentigramaUrlInput;
let dentigramaOverlaySrc;
let currentImageOverlay = null; // Para almacenar la imagen de los trazos del paciente previamente guardados
let dentigramaContainer; // Referencia al contenedor principal del dentigrama

let modoActual = 'pincel';
let colorPincel = 'rgba(255, 0, 0, 1)'; // Rojo por defecto
let grosorPincel = 4;
let dibujando = false;
let ultimoX = 0;
let ultimoY = 0;
let canvasReady = false; // Indica si el canvas está listo para interactuar

let historial = []; // Para la función de deshacer (SOLO NUEVOS TRAZOS DEL USUARIO)

const devicePixelRatio = window.devicePixelRatio || 1; // Para manejo de pantallas de alta densidad

// --- Funciones Auxiliares (Globalmente accesibles o como parte de window) ---

function getCoords(e) {
    const rect = dentigramaCanvas.getBoundingClientRect();
    let clientX = e.clientX, clientY = e.clientY;
    if (e.touches && e.touches.length) {
        clientX = e.touches.clientX;
        clientY = e.touches.clientY;
    }
    return {
        x: (clientX - rect.left),
        y: (clientY - rect.top)
    };
}

function dibujarCheckVectorial(ctx, x, y, size = 15, color = 'rgba(128, 0, 128, 1)', lineWidth = 4) {
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    ctx.beginPath();
    ctx.moveTo(x - size * 0.4, y);
    ctx.lineTo(x - size * 0.1, y + size * 0.4);
    ctx.lineTo(x + size * 0.4, y - size * 0.4);
    ctx.stroke();
}

async function loadImageAsync(url) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = 'Anonymous';
        img.src = url;
        img.onload = () => resolve(img);
        img.onerror = (e) => {
            console.error(`Failed to load image from ${url}`, e);
            reject(new Error(`Failed to load image from ${url}`));
        };
    });
}

// --- Funciones Principales ---

// Función para redimensionar el canvas y redibujar
function resizeCanvas() {
    if (dentigramaContainer && dentigramaCanvas) {
        if (dentigramaContainer.offsetWidth === 0 || dentigramaContainer.offsetHeight === 0) {
            console.warn("DENTIGRAMA WARNING: Contenedor con dimensiones cero al intentar redimensionar. El dentigrama puede estar oculto.");
            canvasReady = false;
            return false; // Indica que no se pudo redimensionar
        }
        
        const containerWidth = dentigramaContainer.clientWidth;
        const containerHeight = dentigramaContainer.clientHeight;

        dentigramaCanvas.width = containerWidth * devicePixelRatio;
        dentigramaCanvas.height = containerHeight * devicePixelRatio;
        ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

        dentigramaCanvas.style.width = containerWidth + 'px';
        dentigramaCanvas.style.height = containerHeight + 'px';

        console.log(`DENTIGRAMA DEBUG: Canvas redimensionado a ${containerWidth}x${containerHeight} (lógico) / ${dentigramaCanvas.width}x${dentigramaCanvas.height} (físico).`);
        
        canvasReady = true;
        redrawAll();
        return true;
    } else {
        console.error("DENTIGRAMA ERROR: dentigramaContainer o dentigramaCanvas no definidos para redimensionar.");
        canvasReady = false;
        return false;
    }
}

// Función para redibujar todo el contenido del canvas
function redrawAll() {
    if (!ctx || !dentigramaCanvas) {
        console.error("DENTIGRAMA ERROR: Contexto o Canvas no inicializados para redrawAll.");
        return;
    }
    ctx.clearRect(0, 0, dentigramaCanvas.width / devicePixelRatio, dentigramaCanvas.height / devicePixelRatio);
    
    // Dibuja el overlay (imagen de trazos original) si existe
    if (currentImageOverlay) {
        ctx.drawImage(currentImageOverlay, 0, 0, dentigramaCanvas.width / devicePixelRatio, dentigramaCanvas.height / devicePixelRatio);
    }

    // Dibuja los trazos del historial (los nuevos trazos del usuario)
    historial.forEach(accion => {
        if (accion.tipo === 'linea') {
            ctx.beginPath();
            ctx.strokeStyle = accion.color;
            ctx.lineWidth = accion.grosor;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            accion.trazos.forEach((punto, index) => {
                if (index === 0) {
                    ctx.moveTo(punto.x * dentigramaCanvas.clientWidth, punto.y * dentigramaCanvas.clientHeight);
                } else {
                    ctx.lineTo(punto.x * dentigramaCanvas.clientWidth, punto.y * dentigramaCanvas.clientHeight);
                }
            });
            ctx.stroke();
        } else if (accion.tipo === 'check') {
            dibujarCheckVectorial(
                ctx,
                accion.x * dentigramaCanvas.clientWidth,
                accion.y * dentigramaCanvas.clientHeight,
                accion.size,
                accion.color,
                accion.grosor
            );
        }
    });
    console.log("DENTIGRAMA DEBUG: redrawAll called. Historial:", historial.length > 0 ? 'con trazos' : 'vacío');
}


// --- Manejadores de Eventos del Pincel ---
function iniciarDibujo(e) {
    if (!canvasReady) { console.warn("DENTIGRAMA WARNING: Canvas no listo para dibujar."); return; }
    const { x, y } = getCoords(e);
    
    if (modoActual === 'pincel') {
        dibujando = true;
        ultimoX = x / dentigramaCanvas.clientWidth; 
        ultimoY = y / dentigramaCanvas.clientHeight;
        historial.push({ tipo: 'linea', color: colorPincel, grosor: grosorPincel, trazos: [{ x: ultimoX, y: ultimoY }] });
    } else if (modoActual === 'check') {
        historial.push({
            tipo: 'check',
            x: x / dentigramaCanvas.clientWidth,
            y: y / dentigramaCanvas.clientHeight,
            size: 30,
            color: 'rgba(128, 0, 128, 1)', // Color del check (púrpura)
            grosor: 6
        });
        redrawAll();
        modoActual = 'pincel';
        actualizarEstadoBotones();
    }
}

function dibujar(e) {
    if (!dibujando || modoActual !== 'pincel' || !canvasReady) return;
    const { x, y } = getCoords(e);
    
    if (historial.length > 0 && historial[historial.length - 1].tipo === 'linea') {
        historial[historial.length - 1].trazos.push({ x: x / dentigramaCanvas.clientWidth, y: y / dentigramaCanvas.clientHeight });
    }

    ctx.strokeStyle = colorPincel;
    ctx.lineWidth = grosorPincel;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineTo(x, y);
    ctx.stroke();

    ultimoX = x / dentigramaCanvas.clientWidth;
    ultimoY = y / dentigramaCanvas.clientHeight;
}

function pararDibujo() {
    if (!canvasReady) return;
    dibujando = false;
    ctx.beginPath();
}


// --- Funciones para la Barra de Control ---
function actualizarEstadoBotones() {
    document.querySelectorAll('.dentigrama-controls .btn').forEach(btn => {
        btn.classList.remove('active');
    });

    if (modoActual === 'pincel') {
        if (colorPincel === 'rgba(255, 0, 0, 1)') document.getElementById('btnColorRojo')?.classList.add('active');
        else if (colorPincel === 'rgba(0, 0, 255, 1)') document.getElementById('btnColorAzul')?.classList.add('active');
        else if (colorPincel === 'rgba(0, 0, 0, 1)') document.getElementById('btnColorNegro')?.classList.add('active');
    } else if (modoActual === 'check') {
        document.getElementById('btnActivarCheck')?.classList.add('active');
    }
}

window.cambiarColor = function(color) {
    if (!canvasReady) { console.warn("DENTIGRAMA WARNING: Canvas no listo para cambiar color."); return; }
    if (color === 'red') {
        colorPincel = 'rgba(255, 0, 0, 1)';
    } else if (color === 'blue') {
        colorPincel = 'rgba(0, 0, 255, 1)';
    } else if (color === 'black') {
        colorPincel = 'rgba(0, 0, 0, 1)';
    }
    modoActual = 'pincel';
    grosorPincel = 4;
    actualizarEstadoBotones();
};

window.activarCheck = function() {
    if (!canvasReady) { console.warn("DENTIGRAMA WARNING: Canvas no listo para activar check."); return; }
    modoActual = 'check';
    grosorPincel = 8;
    actualizarEstadoBotones();
};

window.limpiarCanvas = function() {
    if (!canvasReady) { console.warn("DENTIGRAMA WARNING: Canvas no listo para limpiar."); return; }
    historial = [];
    
    if (dentigramaUrlInput && dentigramaUrlInput.value && !currentImageOverlay) {
        dentigramaUrlInput.value = '';
        console.log("DENTIGRAMA DEBUG: dentigramaUrlInput.value limpiado.");
    }
    
    redrawAll();
    console.log("DENTIGRAMA DEBUG: Canvas limpiado. Historial actual:", historial.length);
};

window.deshacer = function() {
    if (!canvasReady) { console.warn("DENTIGRAMA WARNING: Canvas no listo para deshacer."); return; }
    if (historial.length > 0) {
        const lastAction = historial[historial.length - 1];
        if (lastAction.tipo === 'linea' && lastAction.trazos.length > 1) {
            lastAction.trazos.pop();
            if (lastAction.trazos.length === 0) {
                 historial.pop();
            }
        } else {
            historial.pop();
        }
        redrawAll();
        console.log("DENTIGRAMA DEBUG: Acción deshecha. Historial actual:", historial.length);
    } else {
        console.warn("DENTIGRAMA ADVERTENCIA: No hay acciones para deshacer.");
    }
};



window.guardarDentigramaEnCloudinary = async function() {
    console.log("DENTIGRAMA: guardarDentigramaEnCloudinary called."); 
    if (!canvasReady) {
        alert('El dentigrama aún se está cargando o no se pudo inicializar. Inténtalo de nuevo en unos segundos.');
        return null;
    }

    const btnGuardar = document.getElementById('btnGuardarDentigrama');
    if (btnGuardar && btnGuardar.disabled) {
        console.log("DENTIGRAMA: Botón de guardar ya deshabilitado, ignorando segundo clic.");
        return null; 
    }
    if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.textContent = 'Guardando...'; // Cambia el texto del botón
    }

    const hasDrawnContent = historial.some(accion => accion.tipo === 'linea' || accion.tipo === 'check');
    const dentigramaWasCleanedCompletely = (!currentImageOverlay && !hasDrawnContent && dentigramaUrlInput && dentigramaUrlInput.value);
    
    // Si no hay contenido dibujado, no hay overlay previo Y tampoco hay una URL ya en el input,
    // significa que no hay cambios o no hay nada que guardar.
    // Esto evita guardar un dentigrama vacío si no se ha limpiado uno previo.
    if (!hasDrawnContent && !currentImageOverlay && !dentigramaUrlInput.value) {
        alert('No hay cambios nuevos en el dentigrama para aplicar (ni trazos ni limpieza total).');
        if (btnGuardar) {
            btnGuardar.disabled = false;
            btnGuardar.textContent = '💾 Aplicar Cambios al Dentigrama';
        }
        return '';
    }
    
    try {
        const tempCanvas = document.createElement('canvas');
        tempCanvas.width = dentigramaCanvas.width; 
        tempCanvas.height = dentigramaCanvas.height;
        const tempCtx = tempCanvas.getContext('2d');
        tempCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0); 
        
        // --- Paso 1: Dibujar la plantilla de fondo (odontograma base) ---
        const plantillaFondo = new Image();
        plantillaFondo.crossOrigin = 'Anonymous';
        const fondoUrl = dentigramaContainer.style.backgroundImage.slice(5, -2); // Extrae la URL del background-image CSS
        
        if (fondoUrl && !fondoUrl.includes('undefined') && !fondoUrl.includes('null')) {
            plantillaFondo.src = fondoUrl;
            await new Promise((resolve) => {
                plantillaFondo.onload = () => {
                    tempCtx.drawImage(plantillaFondo, 0, 0, dentigramaCanvas.clientWidth, dentigramaCanvas.clientHeight);
                    resolve();
                };
                plantillaFondo.onerror = () => {
                    console.warn("DENTIGRAMA WARNING: No se pudo cargar la plantilla de fondo del dentigrama para guardar. Dibujando sin fondo.");
                    resolve();
                };
            });
        } else {
            console.warn("DENTIGRAMA WARNING: URL de plantilla de fondo no válida o vacía. Saltando carga de fondo.");
        }

        // --- Paso 2: Dibujar la imagen de trazos previamente guardada (currentImageOverlay) ---
        // Esto es importante para mantener los trazos previos si el usuario solo añade más.
        if (currentImageOverlay) {
            tempCtx.drawImage(currentImageOverlay, 0, 0, dentigramaCanvas.clientWidth, dentigramaCanvas.clientHeight);
            console.log("DENTIGRAMA DEBUG: currentImageOverlay dibujado en tempCanvas.");
        }

        // --- Paso 3: Dibujar los nuevos trazos del historial (líneas y checks) ---
        historial.forEach(accion => { 
            if (accion.tipo === 'linea') {
                tempCtx.beginPath();
                tempCtx.strokeStyle = accion.color;
                tempCtx.lineWidth = accion.grosor;
                tempCtx.lineCap = 'round';
                tempCtx.lineJoin = 'round';
                accion.trazos.forEach((punto, index) => {
                    if (index === 0) {
                        tempCtx.moveTo(punto.x * dentigramaCanvas.clientWidth, punto.y * dentigramaCanvas.clientHeight);
                    } else {
                        tempCtx.lineTo(punto.x * dentigramaCanvas.clientWidth, punto.y * dentigramaCanvas.clientHeight);
                    }
                });
                tempCtx.stroke();
            } else if (accion.tipo === 'check') {
                dibujarCheckVectorial(
                    tempCtx,
                    accion.x * dentigramaCanvas.clientWidth,
                    accion.y * dentigramaCanvas.clientHeight,
                    accion.size,
                    accion.color, 
                    accion.grosor
                );
            }
        });

        const imageDataURL = tempCanvas.toDataURL('image/png');
        console.log("DENTIGRAMA DEBUG: Generated imageDataURL length:", imageDataURL.length);
        
        let patientId = null;
        const patientIdElement = document.getElementById('patientIdHiddenInput');
        
        // **LÓGICA MEJORADA PARA DETERMINAR patientId**
        if (patientIdElement && patientIdElement.value) { // Si el input oculto tiene un valor (es decir, ya existe un paciente)
            patientId = patientIdElement.value;
            console.log("DENTIGRAMA DEBUG: patientId obtenido del input oculto:", patientId);
        } else {
            // Si el input oculto está vacío, estamos en la página de 'crear' o 'editar' sin ID aún.
            // Verificamos si la URL es de edición para un paciente (ej. /pacientes/123/editar)
            const pathSegments = window.location.pathname.split('/');
            const pacientesIndex = pathSegments.indexOf('pacientes');
            // Comprobamos si hay un ID numérico después de '/pacientes/' y antes de '/editar'
            if (pacientesIndex !== -1 && pathSegments.length > pacientesIndex + 1 && !isNaN(parseInt(pathSegments[pacientesIndex + 1]))) {
                 patientId = pathSegments[pacientesIndex + 1];
                 console.log("DENTIGRAMA DEBUG: patientId obtenido de la URL (página de edición):", patientId);
            } else {
                // Si no se encuentra un ID en el input oculto ni en la URL, asumimos que es un nuevo paciente.
                console.log("DENTIGRAMA DEBUG: No se pudo determinar patientId, asumiendo escenario de nuevo paciente (crear).");
                patientId = null; // Explícitamente null para nuevos pacientes
            }
        }
        // **FIN LÓGICA MEJORADA**

        // Ahora, el error "No se pudo determinar el ID del paciente" se manejará en el backend.
        // No necesitamos un 'if (!patientId)' aquí que muestre un alert y detenga la ejecución.
        // El backend deberá saber cómo proceder si patient_id es null.

        const response = await fetch('/pacientes/upload_dentigrama', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image_data: imageDataURL, patient_id: patientId }), // patientId puede ser null
        });

        if (!response.ok) { 
            const errorData = await response.json();
            throw new Error(`Error HTTP: ${response.status} - ${errorData.error || 'Error desconocido del servidor.'}`);
        }

        const data = await response.json();

        if (data.url) { 
            dentigramaUrlInput.value = data.url; 
            
            // Mensaje de alerta ajustado para nuevos pacientes
            const alertMessage = patientId ? 
                'Dentigrama guardado y subido a Cloudinary. No olvides guardar el formulario principal.' :
                'Dentigrama temporal subido a Cloudinary. Guarda el formulario principal para asociarlo al nuevo paciente.';
            alert(alertMessage);

            console.log('DENTIGRAMA DEBUG: Dentigrama subido a Cloudinary:', data.url);
            
            // Actualiza el overlay y limpia el historial local después de una subida exitosa
            currentImageOverlay = await loadImageAsync(data.url);
            historial = [];
            redrawAll();
            
            return data.url; 
        } else {
            console.error('DENTIGRAMA ERROR: Respuesta exitosa de Cloudinary, pero no se encontró la URL en el JSON:', data);
            alert('Hubo un error al obtener la URL del dentigrama después de subirlo.');
            throw new Error(data.error || 'Respuesta de subida inesperada: no se encontró la URL.');
        }

    } catch (error) { 
        console.error('DENTIGRAMA ERROR: Error al guardar o subir el dentigrama (catch block):', error);
        alert("Error al aplicar cambios al dentigrama: " + error.message);
        return null; 
    } finally { 
        if (btnGuardar) {
            btnGuardar.disabled = false;
            btnGuardar.textContent = '💾 Aplicar Cambios al Dentigrama';
        }
    }
};

// ... (resto del código JS) ...


// --- Función de Inicialización Principal (Expuesta Globalmente) ---
// Esta función se llamará cuando la página cargue, y cuando el acordeón del dentigrama se abra.
window.initializeDentigram = function() {
    console.log("DENTIGRAMA: window.initializeDentigram called.");

    // --- ASIGNACIÓN DE VARIABLES GLOBALES (SIN 'const' o 'let' aquí) ---
    // ESTAS ASIGNACIONES DEBEN HACERSE AQUÍ PARA ASEGURAR QUE LAS VARIABLES GLOBALES
    // SE REFERENCIAN A LOS ELEMENTOS DEL DOM CORRECTOS.
    dentigramaContainer = document.getElementById('dentigrama-container');
    dentigramaCanvas = document.getElementById('dentigrama_canvas');
    if (dentigramaCanvas) {
        ctx = dentigramaCanvas.getContext('2d');
    }
    dentigramaUrlInput = document.getElementById('dentigrama_url_input');
    dentigramaOverlaySrc = document.getElementById('dentigrama_overlay_src');
    // --- FIN ASIGNACIÓN ---

    if (!dentigramaCanvas || !dentigramaContainer) {
        console.error("DENTIGRAMA ERROR: Canvas o contenedor no encontrados en window.initializeDentigram.");
        canvasReady = false;
        return;
    }

    // Re-configurar listeners solo si no se han añadido antes
    if (!dentigramaCanvas.dataset.listenersAdded) {
        dentigramaCanvas.addEventListener('mousedown', iniciarDibujo);
        dentigramaCanvas.addEventListener('mousemove', dibujar);
        dentigramaCanvas.addEventListener('mouseup', pararDibujo);
        dentigramaCanvas.addEventListener('mouseout', pararDibujo);
        
        dentigramaCanvas.addEventListener('touchstart', iniciarDibujo, { passive: false });
        dentigramaCanvas.addEventListener('touchmove', dibujar, { passive: false });
        dentigramaCanvas.addEventListener('touchend', pararDibujo);

        window.addEventListener('resize', resizeCanvas);
        dentigramaCanvas.dataset.listenersAdded = 'true';
        console.log("DENTIGRAMA DEBUG: Listeners de dibujo y redimensionamiento añadidos.");
    }

    if (!resizeCanvas()) {
        console.log("DENTIGRAMA DEBUG: Contenedor aún oculto, esperando evento de acordeón para reinicializar.");
        return;
    }

    const initialDentigramUrl = dentigramaUrlInput ? dentigramaUrlInput.value : (dentigramaOverlaySrc ? dentigramaOverlaySrc.src : null);
    
    if (initialDentigramUrl && initialDentigramUrl.length > 0 && !initialDentigramUrl.includes('undefined') && !initialDentigramUrl.includes('null') && initialDentigramUrl !== window.location.href) {
        console.log("DENTIGRAMA DEBUG: Intentando cargar overlay inicial desde:", initialDentigramUrl);
        loadImageAsync(initialDentigramUrl)
            .then(img => {
                currentImageOverlay = img;
                historial = [];
                redrawAll();
                console.log('DENTIGRAMA DEBUG: Overlay previo de Cloudinary cargado y dibujado. Canvas listo.');
            })
            .catch(error => {
                console.error("DENTIGRAMA ERROR: ¡FALLÓ LA CARGA DE LA IMAGEN DE OVERLAY! Error:", error.message);
                currentImageOverlay = null;
                historial = [];
                redrawAll();
            });
    } else {
        console.log('DENTIGRAMA DEBUG: No hay overlay previo. Canvas listo para dibujar (sin imagen de fondo).');
        currentImageOverlay = null;
        historial = [];
        redrawAll();
    }
    
    actualizarEstadoBotones();
};


// --- Event Listeners DOMContentLoaded para la inicialización inicial de la página ---
document.addEventListener('DOMContentLoaded', function() {
    console.log("DENTIGRAMA: DOMContentLoaded fired for editor_dentigrama.js.");
    
    // Adjuntar listeners de botones de control.
    // Estos listeners llaman a funciones globales que ya tienen las comprobaciones de canvasReady.
    document.getElementById('btnColorRojo')?.addEventListener('click', () => cambiarColor('red'));
    document.getElementById('btnColorAzul')?.addEventListener('click', () => cambiarColor('blue'));
    document.getElementById('btnColorNegro')?.addEventListener('click', () => cambiarColor('black'));
    document.getElementById('btnActivarCheck')?.addEventListener('click', activarCheck);
    document.getElementById('btnLimpiar')?.addEventListener('click', limpiarCanvas);
    document.getElementById('btnDeshacer')?.addEventListener('click', deshacer); 
    
    const btnGuardarDentigrama_ref = document.getElementById('btnGuardarDentigrama');
    if (btnGuardarDentigrama_ref) { 
        btnGuardarDentigrama_ref.removeEventListener('click', window.guardarDentigramaEnCloudinary); 
        btnGuardarDentigrama_ref.addEventListener('click', window.guardarDentigramaEnCloudinary); 
    } else {
        console.warn("DENTIGRAMA: Botón 'btnGuardarDentigrama' no encontrado para adjuntar listener.");
    }

    // Comprobación e inicialización temprana si el contenedor del dentigrama es visible al cargar el DOM.
    // Aquí es donde se llama a window.initializeDentigram por primera vez si el acordeón está abierto.
    // initializeDentigram es la que se encarga de asignar todas las variables globales y el resto.
    const tempDentigramaContainer = document.getElementById('dentigrama-container'); 
    if (tempDentigramaContainer && tempDentigramaContainer.offsetWidth > 0 && tempDentigramaContainer.offsetHeight > 0) {
        console.log("DENTIGRAMA: Inicializando Dentigrama en DOMContentLoaded (visible).");
        window.initializeDentigram();
    } else {
        console.log("DENTIGRAMA: Contenedor no visible en DOMContentLoaded. Se inicializará al abrir el acordeón.");
    }
});