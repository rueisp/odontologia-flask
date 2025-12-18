// Archivo: clinica/static/js/editor_dentigrama.js
// VERSIÓN UNIFICADA: CAMBIO DE COLOR NEGRO A VERDE

// --- Variables Globales ---
let dentigramaCanvas;
let ctx;
let dentigramaUrlInput;
let dentigramaOverlaySrc;
let currentImageOverlay = null; 
let dentigramaContainer; 

let modoActual = 'pincel';
let colorPincel = 'rgba(255, 0, 0, 1)'; // Rojo por defecto
let grosorPincel = 4;
let dibujando = false;
let ultimoX = 0;
let ultimoY = 0;
let canvasReady = false; 

let historial = []; 

const devicePixelRatio = window.devicePixelRatio || 1; 

// --- Funciones Auxiliares ---

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

function resizeCanvas() {
    if (dentigramaContainer && dentigramaCanvas) {
        if (dentigramaContainer.offsetWidth === 0 || dentigramaContainer.offsetHeight === 0) {
            canvasReady = false;
            return false; 
        }
        
        const containerWidth = dentigramaContainer.clientWidth;
        const containerHeight = dentigramaContainer.clientHeight;

        dentigramaCanvas.width = containerWidth * devicePixelRatio;
        dentigramaCanvas.height = containerHeight * devicePixelRatio;
        ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

        dentigramaCanvas.style.width = containerWidth + 'px';
        dentigramaCanvas.style.height = containerHeight + 'px';
        
        canvasReady = true;
        redrawAll();
        return true;
    } else {
        canvasReady = false;
        return false;
    }
}

function redrawAll() {
    if (!ctx || !dentigramaCanvas) return;
    
    ctx.clearRect(0, 0, dentigramaCanvas.width / devicePixelRatio, dentigramaCanvas.height / devicePixelRatio);
    
    if (currentImageOverlay) {
        ctx.drawImage(currentImageOverlay, 0, 0, dentigramaCanvas.width / devicePixelRatio, dentigramaCanvas.height / devicePixelRatio);
    }

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
}

// --- Manejadores de Eventos del Pincel ---
function iniciarDibujo(e) {
    if (!canvasReady) return;
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
            color: 'rgba(128, 0, 128, 1)', 
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
        // MODIFICADO: AHORA BUSCAMOS EL BOTÓN VERDE
        else if (colorPincel === 'rgba(0, 128, 0, 1)') document.getElementById('btnColorVerde')?.classList.add('active');
    } else if (modoActual === 'check') {
        document.getElementById('btnActivarCheck')?.classList.add('active');
    }
}

window.cambiarColor = function(color) {
    if (!canvasReady) return;
    if (color === 'red') {
        colorPincel = 'rgba(255, 0, 0, 1)';
    } else if (color === 'blue') {
        colorPincel = 'rgba(0, 0, 255, 1)';
    } else if (color === 'green') { // NUEVO: Color Verde
        colorPincel = 'rgba(0, 128, 0, 1)';
    }
    modoActual = 'pincel';
    grosorPincel = 4;
    actualizarEstadoBotones();
};

window.activarCheck = function() {
    if (!canvasReady) return;
    modoActual = 'check';
    grosorPincel = 8;
    actualizarEstadoBotones();
};

window.limpiarCanvas = function() {
    if (!canvasReady) return;
    historial = [];
    if (dentigramaUrlInput && dentigramaUrlInput.value && !currentImageOverlay) {
        dentigramaUrlInput.value = '';
    }
    redrawAll();
};

window.deshacer = function() {
    if (!canvasReady) return;
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
    }
};

window.guardarDentigramaEnCloudinary = async function() {
    if (!canvasReady) {
        alert('El dentigrama aún se está cargando. Inténtalo de nuevo.');
        return null;
    }

    const btnGuardar = document.getElementById('btnGuardarDentigrama');
    if (btnGuardar && btnGuardar.disabled) return null; 
    
    if (btnGuardar) {
        btnGuardar.disabled = true;
        btnGuardar.textContent = 'Guardando...';
    }

    const hasDrawnContent = historial.some(accion => accion.tipo === 'linea' || accion.tipo === 'check');
    if (!hasDrawnContent && !currentImageOverlay && !dentigramaUrlInput.value) {
        alert('No hay cambios nuevos en el dentigrama.');
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
        
        const plantillaFondo = new Image();
        plantillaFondo.crossOrigin = 'Anonymous';
        const fondoUrl = dentigramaContainer.style.backgroundImage.slice(5, -2);
        
        if (fondoUrl && !fondoUrl.includes('undefined') && !fondoUrl.includes('null')) {
            plantillaFondo.src = fondoUrl;
            await new Promise((resolve) => {
                plantillaFondo.onload = () => {
                    tempCtx.drawImage(plantillaFondo, 0, 0, dentigramaCanvas.clientWidth, dentigramaCanvas.clientHeight);
                    resolve();
                };
                plantillaFondo.onerror = () => resolve();
            });
        }

        if (currentImageOverlay) {
            tempCtx.drawImage(currentImageOverlay, 0, 0, dentigramaCanvas.clientWidth, dentigramaCanvas.clientHeight);
        }

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
        
        let patientId = null;
        const patientIdElement = document.getElementById('patientIdHiddenInput');
        
        if (patientIdElement && patientIdElement.value) {
            patientId = patientIdElement.value;
        } else {
            const pathSegments = window.location.pathname.split('/');
            const pacientesIndex = pathSegments.indexOf('pacientes');
            if (pacientesIndex !== -1 && pathSegments.length > pacientesIndex + 1 && !isNaN(parseInt(pathSegments[pacientesIndex + 1]))) {
                 patientId = pathSegments[pacientesIndex + 1];
            }
        }

        const response = await fetch('/pacientes/upload_dentigrama', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_data: imageDataURL, patient_id: patientId }),
        });

        if (!response.ok) { 
            const errorData = await response.json();
            throw new Error(errorData.error || 'Error del servidor.');
        }

        const data = await response.json();

        if (data.url) { 
            dentigramaUrlInput.value = data.url; 
            const alertMessage = patientId ? 
                'Dentigrama guardado. No olvides guardar el formulario principal.' :
                'Dentigrama temporal guardado. Guarda el formulario principal.';
            alert(alertMessage);
            currentImageOverlay = await loadImageAsync(data.url);
            historial = [];
            redrawAll();
            return data.url; 
        } else {
            throw new Error('No se recibió la URL.');
        }

    } catch (error) { 
        alert("Error al aplicar cambios: " + error.message);
        return null; 
    } finally { 
        if (btnGuardar) {
            btnGuardar.disabled = false;
            btnGuardar.textContent = '💾 Aplicar Cambios al Dentigrama';
        }
    }
};

window.initializeDentigram = function() {
    dentigramaContainer = document.getElementById('dentigrama-container');
    dentigramaCanvas = document.getElementById('dentigrama_canvas');
    if (dentigramaCanvas) ctx = dentigramaCanvas.getContext('2d');
    dentigramaUrlInput = document.getElementById('dentigrama_url_input');
    dentigramaOverlaySrc = document.getElementById('dentigrama_overlay_src');

    if (!dentigramaCanvas || !dentigramaContainer) {
        canvasReady = false;
        return;
    }

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
    }

    if (!resizeCanvas()) return;

    const initialDentigramUrl = dentigramaUrlInput ? dentigramaUrlInput.value : (dentigramaOverlaySrc ? dentigramaOverlaySrc.src : null);
    
    if (initialDentigramUrl && initialDentigramUrl.length > 0 && !initialDentigramUrl.includes('undefined') && initialDentigramUrl !== window.location.href) {
        loadImageAsync(initialDentigramUrl)
            .then(img => {
                currentImageOverlay = img;
                historial = [];
                redrawAll();
            })
            .catch(error => {
                currentImageOverlay = null;
                historial = [];
                redrawAll();
            });
    } else {
        currentImageOverlay = null;
        historial = [];
        redrawAll();
    }
    
    actualizarEstadoBotones();
};


document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('btnColorRojo')?.addEventListener('click', () => cambiarColor('red'));
    document.getElementById('btnColorAzul')?.addEventListener('click', () => cambiarColor('blue'));
    // MODIFICADO: AHORA ESCUCHAMOS EL BOTÓN VERDE
    document.getElementById('btnColorVerde')?.addEventListener('click', () => cambiarColor('green'));
    
    document.getElementById('btnActivarCheck')?.addEventListener('click', activarCheck);
    document.getElementById('btnLimpiar')?.addEventListener('click', limpiarCanvas);
    document.getElementById('btnDeshacer')?.addEventListener('click', deshacer); 
    
    const btnGuardarDentigrama_ref = document.getElementById('btnGuardarDentigrama');
    if (btnGuardarDentigrama_ref) { 
        btnGuardarDentigrama_ref.removeEventListener('click', window.guardarDentigramaEnCloudinary); 
        btnGuardarDentigrama_ref.addEventListener('click', window.guardarDentigramaEnCloudinary); 
    }

    const tempDentigramaContainer = document.getElementById('dentigrama-container'); 
    if (tempDentigramaContainer && tempDentigramaContainer.offsetWidth > 0 && tempDentigramaContainer.offsetHeight > 0) {
        window.initializeDentigram();
    }
});