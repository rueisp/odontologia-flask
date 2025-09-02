// Reemplaza 'DOMContentLoaded' por 'window.onload' para asegurar que el DOM y el CSS estén completamente renderizados
window.onload = function () {
    const canvas = document.getElementById('dentigrama_canvas');
    if (!canvas) {
        console.warn("DENTIGRAMA: No se encontró el canvas 'dentigrama_canvas'.");
        return;
    }

    const dentigramaContainer = document.getElementById('dentigrama-container');
    if (!dentigramaContainer) {
        console.error("DENTIGRAMA: No se encontró el contenedor 'dentigrama-container'. Por favor, asegúrate de que el div con id='dentigrama-container' exista.");
        return;
    }

    // Limpiar atributos width/height HTML para que CSS y JS los controlen
    if (canvas.hasAttribute('width')) {
        console.warn("DENTIGRAMA: Eliminando atributo 'width' HTML/dinámico del canvas.");
        canvas.removeAttribute('width');
    }
    if (canvas.hasAttribute('height')) {
        console.warn("DENTIGRAMA: Eliminando atributo 'height' HTML/dinámico del canvas.");
        canvas.removeAttribute('height');
    }

    const ctx = canvas.getContext('2d');
    const dentigramaUrlInput = document.getElementById('dentigrama_url_input');

    // --- Configuración de DPI y Dimensiones Lógicas ---
    const devicePixelRatio = window.devicePixelRatio || 1;
    // Obtener las dimensiones lógicas del contenedor, asegurando que el HTML lo tiene definido
    // ESTOS VALORES YA DEBERÍAN SER CORRECTOS AQUÍ
    const logicalWidth = dentigramaContainer.clientWidth; 
    const logicalHeight = dentigramaContainer.clientHeight; 
    
    // --- VERIFICACIÓN ADICIONAL DE DIMENSIONES ---
    if (logicalWidth === 0 || logicalHeight === 0) {
        console.error("DENTIGRAMA ERROR CRÍTICO: El dentigramaContainer reporta dimensiones cero incluso en window.onload. Esto es un problema con el CSS o el layout.");
        return; // No podemos inicializar el canvas si las dimensiones son cero
    }
    console.log(`DENTIGRAMA DEBUG: [window.onload] Dimensiones lógicas obtenidas del contenedor: ${logicalWidth}x${logicalHeight}`);

    // Establecer la resolución interna del canvas para manejar DPI
    canvas.width = logicalWidth * devicePixelRatio;
    canvas.height = logicalHeight * devicePixelRatio;
    
    // Escalar el contexto de dibujo para que todo se dibuje a la resolución lógica
    ctx.scale(devicePixelRatio, devicePixelRatio);

    // --- Variables de Estado ---
    let historial = []; 
    let dibujando = false;
    let colorActual = 'red';
    let modoActual = 'pincel';
    let canvasReady = false; 

    // --- Imágenes (Fondo y Precarga) ---
    const backgroundImageUrl = canvas.dataset.backgroundUrl; 
    const imagenPreviaElemento = document.getElementById('dentigrama_overlay_src'); 
    
    const bgImage = new Image();
    bgImage.crossOrigin = "Anonymous"; 
    
    // El resto del script sigue aquí, incluyendo Promise.all, getCoords, eventos, etc.
    // Asegúrate de que el bloque Promise.all() es la versión más reciente que te di.
    // ... (todo el resto de tu código dentigrama_logic.js) ...

    // --- Funciones Core de Renderizado ---
    const clearCanvas = () => { 
        ctx.save();
        ctx.setTransform(1, 0, 0, 1, 0, 0); // Resetear transformación para limpiar todo el canvas físico
        ctx.clearRect(0, 0, canvas.width, canvas.height); 
        ctx.restore(); // Restaurar la transformación escalada
    };

    const renderCanvasStateFromHistory = (stateIndex) => {
        clearCanvas(); 
        const stateToRender = historial[stateIndex];
        if (stateToRender) {
            ctx.putImageData(stateToRender, 0, 0); 
            console.log(`DENTIGRAMA DEBUG: Estado ${stateIndex} renderizado. Historial actual: ${historial.length}`);
        } else {
            console.error(`DENTIGRAMA ERROR: Intentando renderizar estado ${stateIndex} que no existe en historial. Fallback a dibujar fondo si es posible.`);
            if (bgImage.complete && backgroundImageUrl) {
                ctx.drawImage(bgImage, 0, 0, logicalWidth, logicalHeight); 
            }
        }
    };

    const guardarEstadoActualEnHistorial = () => {
        try {
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            let hasNonZeroPixel = false;
            for(let i=0; i < imageData.data.length; i+=4) { 
                if (imageData.data[i+3] !== 0) { 
                    hasNonZeroPixel = true;
                    break;
                }
            }
            console.log('DENTIGRAMA DEBUG PIXEL CHECK (saving state): El estado que se va a guardar contiene píxeles visibles (no es transparente):', hasNonZeroPixel);

            historial.push(imageData);
            if (historial.length > 20) historial.shift(); 
            console.log("DENTIGRAMA DEBUG: Estado guardado. Longitud del historial:", historial.length);
        } catch (e) {
            console.error("DENTIGRAMA ERROR CRÍTICO: ¡El canvas está contaminado! No se pudo capturar ImageData al guardar estado. El fondo desaparecerá.", e);
        }
    };
    
    // --- Lógica de Carga Inicial Robusta con Promesas ---
    
    // 1. Promesa para cargar la imagen de fondo (plantilla_dentigrama.png)
    const loadBackgroundImagePromise = new Promise(resolve => {
        if (!backgroundImageUrl) {
            console.warn("DENTIGRAMA: No se encontró la URL de la imagen de fondo en data-background-url.");
            resolve(false); // Indica que el fondo no se cargó
            return;
        }
        // AÑADIR CACHE BUSTER
        const urlWithCacheBuster = backgroundImageUrl + '?cb=' + new Date().getTime();
        bgImage.src = urlWithCacheBuster; // Asignar src después de crossOrigin
        
        bgImage.onload = () => {
            console.log("DENTIGRAMA DEBUG: Fondo local cargado OK.");
            resolve(true); // Indica que el fondo se cargó con éxito
        };
        bgImage.onerror = () => {
            console.error("DENTIGRAMA ERROR: AL CARGAR IMAGEN DE FONDO LOCAL:", urlWithCacheBuster);
            resolve(false); // Indica que hubo un error al cargar el fondo
        };
    });

    // 2. Promesa para cargar la imagen de overlay (de Cloudinary) si existe
    const loadOverlayImagePromise = new Promise(resolve => {
        if (!(imagenPreviaElemento && imagenPreviaElemento.src && imagenPreviaElemento.src !== window.location.href)) {
            resolve(null); // No hay overlay o URL inválida
            return;
        }
        const imgOverlay = new Image();
        imgOverlay.crossOrigin = 'Anonymous';
        imgOverlay.src = imagenPreviaElemento.src;
        imgOverlay.onload = () => {
            console.log("DENTIGRAMA DEBUG: Overlay previo de Cloudinary cargado OK.");
            resolve(imgOverlay); // Resuelve con el objeto Image
        };
        imgOverlay.onerror = () => {
            console.error('DENTIGRAMA ERROR: AL CARGAR TRAZOS PREVIOS DE CLOUDINARY:', imagenPreviaElemento.src, "-> POSIBLE PROBLEMA CORS o URL no válida.");
            resolve(null); // Hubo un error al cargar el overlay
        };
    });

    // 3. Unir ambas promesas para construir el estado inicial del canvas
    Promise.all([loadBackgroundImagePromise, loadOverlayImagePromise])
        .then(([isBgLoaded, imgOverlay]) => {
            console.log("DENTIGRAMA DEBUG: Ambas promesas de carga inicial resueltas. isBgLoaded:", isBgLoaded);
            // --- NUEVOS LOGS DE DEPURACIÓN CRÍTICA (canvas principal) ---
            console.log("DENTIGRAMA DEBUG: [Promesa All] Dimensiones del canvas principal: canvas.width =", canvas.width, ", canvas.height =", canvas.height);
            // --- FIN NUEVOS LOGS ---

            const tempCanvas = document.createElement('canvas'); 
            // Asignar dimensiones al tempCanvas directamente usando logicalWidth/Height escalado por DPI
            tempCanvas.width = logicalWidth * devicePixelRatio; 
            tempCanvas.height = logicalHeight * devicePixelRatio;
            console.log("DENTIGRAMA DEBUG: [Promesa All] Dimensiones del tempCanvas asignadas: tempCanvas.width =", tempCanvas.width, ", tempCanvas.height =", tempCanvas.height);
            
            const tempCtx = tempCanvas.getContext('2d');
            tempCtx.scale(devicePixelRatio, devicePixelRatio); 
            
            // Dibujar el fondo
            if (isBgLoaded) { // Solo dibuja si la promesa confirmó que cargó
                // --- NUEVOS LOGS DE DEPURACIÓN CRÍTICA Y VERIFICACIÓN (bgImage) ---
                console.log("DENTIGRAMA DEBUG CRÍTICO: isBgLoaded es TRUE. bgImage.complete:", bgImage.complete, "bgImage.width:", bgImage.width, "bgImage.height:", bgImage.height);
                if (bgImage.complete && bgImage.width > 0 && bgImage.height > 0) {
                    tempCtx.drawImage(bgImage, 0, 0, logicalWidth, logicalHeight);
                    console.log("DENTIGRAMA DEBUG: Fondo local dibujado en tempCanvas.");
                } else {
                    console.error("DENTIGRAMA ERROR CRÍTICO: isBgLoaded es TRUE, pero bgImage NO está completa o tiene dimensiones cero. No se pudo dibujar el fondo. Intentando con un pequeño retraso...");
                    // --- INTENTO DE DIBUJO CON RETRASO ---
                    setTimeout(() => {
                        if (bgImage.complete && bgImage.width > 0 && bgImage.height > 0) {
                            tempCtx.drawImage(bgImage, 0, 0, logicalWidth, logicalHeight);
                            console.log("DENTIGRAMA DEBUG: Fondo local dibujado en tempCanvas DESPUÉS DE RETRASO.");
                        } else {
                            console.error("DENTIGRAMA ERROR CRÍTICO: Fallo al dibujar el fondo incluso con retraso. La imagen puede ser inválida o hay un problema más profundo.");
                        }
                    }, 50); // Pequeño retraso de 50ms
                    // --- FIN INTENTO DE DIBUJO CON RETRASO ---
                }
                // --- FIN NUEVOS LOGS ---
            } else {
                console.warn("DENTIGRAMA DEBUG: Fondo local NO dibujado en tempCanvas (la promesa indicó que no cargó).");
            }

            // Dibujar el overlay (si cargó)
            if (imgOverlay) {
                try {
                    tempCtx.drawImage(imgOverlay, 0, 0, logicalWidth, logicalHeight);
                    console.log("DENTIGRAMA DEBUG: Overlay de Cloudinary dibujado en tempCanvas.");
                } catch (e) {
                    console.error("DENTIGRAMA ERROR: Canvas contaminado al dibujar overlay de Cloudinary en tempCanvas.", e);
                }
            }

            let baseImageData;
            try {
                baseImageData = tempCtx.getImageData(0, 0, tempCanvas.width, tempCanvas.height);
                console.log("DENTIGRAMA DEBUG: baseImageData capturada de tempCanvas.");
            } catch (e) {
                console.error("DENTIGRAMA ERROR CRÍTICO: No se pudo capturar baseImageData inicial (fondo + overlay) de tempCanvas. ¡Canvas contaminado!", e);
                baseImageData = tempCtx.createImageData(tempCanvas.width, tempCanvas.height); // Fallback transparente
            }
            historial.push(baseImageData);

            // --- AQUI EL NUEVO LOG CLAVE ---
            const hasContentInFirstState = historial.length > 0 && historial[0].data.some(val => val !== 0);
            console.log('DENTIGRAMA DEBUG: hasContentInFirstState for historial[0] (después de captura):', hasContentInFirstState);

            // Finalmente, dibujar el estado inicial en el canvas principal
            if (hasContentInFirstState) { // Usa esta variable para la condición
                renderCanvasStateFromHistory(0);
                canvasReady = true;
                console.log('DENTIGRAMA DEBUG: Canvas inicializado y listo. Longitud del historial:', historial.length);
            } else {
                console.error("DENTIGRAMA ERROR CRÍTICO: El historial no se inicializó con baseImageData o el primer estado está vacío. Intentando dibujar fondo directamente.");
                clearCanvas();
                // Si el isBgLoaded es true, intentar dibujar el fondo en el canvas principal también como fallback
                if (isBgLoaded && bgImage.complete && bgImage.width > 0 && bgImage.height > 0) { 
                    ctx.drawImage(bgImage, 0, 0, logicalWidth, logicalHeight);
                    try { 
                        historial.push(ctx.getImageData(0,0,canvas.width,canvas.height)); 
                        console.warn("DENTIGRAMA ADVERTENCIA: Historial[0] corregido con solo fondo local si estaba vacío/falló.");
                    } catch (e) {
                        console.error("DENTIGRAMA ERROR: No se pudo guardar estado de emergencia por 'canvas contaminado'.", e);
                    }
                } else {
                     console.warn("DENTIGRAMA ADVERTENCIA: No se pudo dibujar el fondo de emergencia (no cargado o dimensiones cero).");
                }
                canvasReady = true; // Marcar como listo para permitir dibujar, aunque el fondo pueda faltar.
            }
            console.log('DENTIGRAMA DEBUG: Canvas Ready: TRUE'); 
        })
        .catch(error => {
            console.error("DENTIGRAMA ERROR: Fallo en una de las promesas de carga inicial del dentigrama:", error);
            canvasReady = true; // Intentar marcar como listo para permitir alguna interacción.
        });
    // --- Utilidades: getCoords (funciona asumiendo 100% de zoom) ---
    const getCoords = (e) => {
        const rect = canvas.getBoundingClientRect();

        let clientX = e.clientX;
        let clientY = e.clientY;
        if (e.touches && e.touches.length) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        }

        console.log('DENTIGRAMA getCoords DEBUG: --- Inicio Evento de Mouse ---');
        console.log('DENTIGRAMA getCoords DEBUG: rect.width:', rect.width, 'rect.height:', rect.height);
        console.log('DENTIGRAMA getCoords DEBUG: rect.left:', rect.left, 'rect.top:', rect.top);
        console.log('DENTIGRAMA getCoords DEBUG: clientX (viewport):', clientX, 'clientY (viewport):', clientY);
        console.log('DENTIGRAMA getCoords DEBUG: logicalWidth (JS):', logicalWidth, 'logicalHeight (JS):', logicalHeight);
        
        if (rect.width === 0 || rect.height === 0) {
            console.error('DENTIGRAMA CRÍTICO: getBoundingClientRect() reportó ancho/alto cero durante el dibujo. No se puede calcular la posición.');
            return { x: 0, y: 0 }; 
        }

        const finalX = (clientX - rect.left) * (logicalWidth / rect.width);
        const finalY = (clientY - rect.top) * (logicalHeight / rect.height);

        console.log('DENTIGRAMA getCoords DEBUG: Coordenadas finales calculadas: finalX:', finalX, 'finalY:', finalY);
        console.log('DENTIGRAMA getCoords DEBUG: --- Fin Evento de Mouse ---');

        return { x: finalX, y: finalY };
    };

    // --- Funciones de Dibujo (el resto de este código debería estar bien) ---
    const empezarDibujo = (e) => {
        if (!canvasReady) { console.warn("DENTIGRAMA: Canvas no listo, ignorando empezarDibujo."); return; }
        dibujando = true;
        const { x, y } = getCoords(e);
        ctx.beginPath();
        ctx.strokeStyle = colorActual;
        ctx.lineWidth = 4;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round'; 
        ctx.moveTo(x, y); 
        console.log("DENTIGRAMA DEBUG: empezarDibujo en", x, y, "con color", colorActual);
    };

    const dibujar = (e) => {
        if (!dibujando || !canvasReady) return;
        const { x, y } = getCoords(e);
        ctx.lineTo(x, y);
        ctx.stroke();
    };

    const finalizarDibujo = () => {
        if (!dibujando || !canvasReady) return;
        dibujando = false;
        guardarEstadoActualEnHistorial(); 
        console.log("DENTIGRAMA DEBUG: finalizarDibujo. Estado guardado. Historial longitud:", historial.length);
    };

    // --- Eventos de Puntero (mouse y touch) ---
    canvas.addEventListener('mousedown', (e) => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') {
            e.preventDefault();
            empezarDibujo(e);
        } else if (modoActual === 'check') {
            const { x, y } = getCoords(e);
            ctx.font = 'bold 30px Arial';
            ctx.fillStyle = colorActual; 
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('✔️', x, y);
            guardarEstadoActualEnHistorial(); 
            
            modoActual = 'pincel';
            colorActual = 'black'; 
            canvas.style.cursor = 'default';
            actualizarEstadoBotones();
            console.log("DENTIGRAMA DEBUG: Check colocado en", x, y);
        }
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') dibujar(e);
    });

    canvas.addEventListener('mouseup', () => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') {
            finalizarDibujo();
        }
    });

    canvas.addEventListener('mouseout', () => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') finalizarDibujo();
    });

    canvas.addEventListener('touchstart', (e) => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') {
            e.preventDefault();
            empezarDibujo(e);
        }
    }, { passive: false });

    canvas.addEventListener('touchmove', (e) => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') {
            e.preventDefault();
            dibujar(e);
        }
    }, { passive: false });

    canvas.addEventListener('touchend', (e) => {
        if (!canvasReady) return;
        if (modoActual === 'pincel') {
            e.preventDefault();
            finalizarDibujo();
        }
    }, { passive: false });

    // --- Botonera ---
    const cambiarColor = (nuevoColor) => {
        if (!canvasReady) return;
        colorActual = nuevoColor;
        modoActual = 'pincel';
        canvas.style.cursor = 'default';
        actualizarEstadoBotones();
        console.log("DENTIGRAMA DEBUG: Color cambiado a", nuevoColor);
    };

    const activarHerramientaCheck = () => {
        if (!canvasReady) return;
        colorActual = 'blue'; 
        modoActual = 'check';
        canvas.style.cursor = 'crosshair';
        actualizarEstadoBotones();
        console.log("DENTIGRAMA DEBUG: Modo Check activado.");
    };

    const limpiarCanvas = () => {
        if (!canvasReady) return;
        console.log("DENTIGRAMA DEBUG: Ejecutando limpiarCanvas. Longitud historial antes:", historial.length);
        
        if (historial.length > 0) {
            historial = [historial[0]]; // Restablecer a UN solo estado: la base completa (fondo + overlay si existía)
            renderCanvasStateFromHistory(0); // Renderizar esa base
            console.log("DENTIGRAMA DEBUG: Canvas limpiado a estado inicial. Historial longitud:", historial.length);
        } else {
            console.warn("DENTIGRAMA ADVERTENCIA: Historial vacío al intentar limpiar canvas. Re-dibujando fondo directamente.");
            clearCanvas(); 
            if (bgImage.complete && backgroundImageUrl) { // Usa isBgLoaded aquí si tuvieras la flag en este scope
                ctx.drawImage(bgImage, 0, 0, logicalWidth, logicalHeight);
                try {
                    historial.push(ctx.getImageData(0,0,canvas.width,canvas.height));
                } catch (e) {
                     console.error("DENTIGRAMA ERROR: No se pudo guardar estado de emergencia al limpiar por 'canvas contaminado'.", e);
                }
            }
        }
    };

    const deshacer = () => {
        if (!canvasReady) return;
        console.log("DENTIGRAMA DEBUG: Ejecutando deshacer. Longitud historial antes de pop:", historial.length);
        if (historial.length > 1) { 
            historial.pop(); 
            renderCanvasStateFromHistory(historial.length - 1); 
            console.log("DENTIGRAMA DEBUG: Deshecho. Historial longitud:", historial.length);
        } else if (historial.length === 1) { 
            renderCanvasStateFromHistory(0); 
            console.log("DENTIGRAMA DEBUG: Deshecho. Solo queda estado inicial. Historial longitud:", historial.length);
        } else {
            console.warn("DENTIGRAMA ADVERTENCIA: No hay estados en el historial para deshacer.");
        }
    };

    const accionBotonGuardarCanvas = () => {
        if (!canvasReady) {
             alert('El dentigrama aún se está cargando o no se pudo inicializar. Inténtalo de nuevo en unos segundos.');
             return;
        }
        const ultimo = historial[historial.length - 1];
        if (!ultimo) {
             alert('No hay nada para guardar en el dentigrama. Por favor, dibuja algo.'); 
             return;
        }

        canvas.toBlob(function (blob) {
            const formData = new FormData();
            formData.append('dentigrama_overlay', blob, 'dentigrama.png');
            fetch('/pacientes/upload_dentigrama', { method: 'POST', body: formData })
                .then(r => r.json())
                .then(d => {
                    if (d.url && dentigramaUrlInput) {
                        dentigramaUrlInput.value = d.url;
                        alert('¡Dentigrama actualizado!\nNo olvides guardar el formulario.');
                        console.log("DENTIGRAMA DEBUG: Dentigrama subido y URL guardada:", d.url);
                    } else {
                        alert('Error al subir el dentigrama: ' + (d.error || 'Respuesta desconocida'));
                        console.error('DENTIGRAMA ERROR: al subir el dentigrama:', d.error || 'Respuesta desconocida');
                    }
                })
                .catch(err => {
                    console.error('DENTIGRAMA ERROR: de red al subir a Cloudinary:', err);
                    alert('Hubo un error de conexión al subir el dentigrama.');
                });
        }, 'image/png');
    };

    function actualizarEstadoBotones() {
        document.querySelectorAll('.btn-color').forEach(btn => { // Usar clase común para los botones de color
            btn.classList.remove('active');
            let targetColor = colorActual;
            if (targetColor === 'red' && btn.id === 'btnColorRojo') btn.classList.add('active');
            else if (targetColor === 'blue' && btn.id === 'btnColorAzul') btn.classList.add('active');
            else if (targetColor === 'black' && btn.id === 'btnColorNegro') btn.classList.add('active');
        });
        document.getElementById('btnActivarCheck')?.classList.toggle('active', modoActual === 'check');
    }

    // Asignación de botones
    document.getElementById('btnColorRojo')?.addEventListener('click', () => cambiarColor('red'));
    document.getElementById('btnColorAzul')?.addEventListener('click', () => cambiarColor('blue'));
    document.getElementById('btnColorNegro')?.addEventListener('click', () => cambiarColor('black'));
    document.getElementById('btnActivarCheck')?.addEventListener('click', activarHerramientaCheck);
    document.getElementById('btnLimpiar')?.addEventListener('click', limpiarCanvas);
    document.getElementById('btnDeshacer')?.addEventListener('click', deshacer);
    document.getElementById('btnGuardarDentigrama')?.addEventListener('click', accionBotonGuardarCanvas);

    // Inicializar el estado de los botones (importante para que se muestre el color inicial)
    actualizarEstadoBotones(); 
};