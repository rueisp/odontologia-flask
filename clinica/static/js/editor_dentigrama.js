// Archivo: clinica/static/js/editor_dentigrama.js
// VERSIÓN V20 - SAFETY LOCK & ANTI-CACHÉ AGRESIVO
// Objetivo: Evitar la pérdida de historial y forzar la visualización actualizada.

console.log("--- EDITOR DENTIGRAMA V20 (SAFETY LOCK) CARGADO ---");

let svgDentigrama;
let herramientaActual = 'caries';
const SVG_NS = "http://www.w3.org/2000/svg";
let tieneFondo = false;
let tempSessionId = null; 

// Configuración de Dientes (Estándar FDI)
const dientesAdultosSup = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28];
const dientesNinosSup   = [55, 54, 53, 52, 51, 61, 62, 63, 64, 65];
const dientesNinosInf   = [85, 84, 83, 82, 81, 71, 72, 73, 74, 75];
const dientesAdultosInf = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38];

document.addEventListener('DOMContentLoaded', function() {
    svgDentigrama = document.getElementById('svgDentigrama');
    
    if (svgDentigrama) {
        // Asegurar ViewBox
        if (!svgDentigrama.hasAttribute('viewBox')) {
            svgDentigrama.setAttribute('viewBox', '0 0 860 480');
        }

        const inputUrl = document.getElementById('dentigrama_url_input');
        const inputId = document.getElementById('patientIdHiddenInput');

        // 1. DETECCIÓN DE FONDO (CRÍTICO)
        // Solo activamos modo "fondo transparente" si hay una URL válida.
        if (inputUrl && inputUrl.value && inputUrl.value !== "None" && inputUrl.value.trim() !== "" && inputUrl.value.startsWith('http')) {
            tieneFondo = true;
            cargarFondoVisual(inputUrl.value);
        } else {
            tieneFondo = false;
        }

        // 2. ID TEMPORAL PARA CREACIÓN
        if (!inputId || !inputId.value || inputId.value === "None") {
            tempSessionId = "temp_" + Date.now();
        }
        
        // 3. RENDERIZADO INICIAL
        renderizarDentigrama();
        setupHerramientas();
        setupGuardadoManual(); // Botón específico del dentigrama
    }
});

/**
 * Carga la imagen de fondo en el CSS del SVG para visualización inmediata.
 * Usa timestamp para romper la caché del navegador.
 */
function cargarFondoVisual(url) {
    const timestamp = new Date().getTime();
    // Forzamos al navegador a pedir una nueva versión a Cloudinary
    const cacheBusterUrl = (url.indexOf('?') > -1 ? '&' : '?') + 't=' + timestamp;
    
    svgDentigrama.style.backgroundImage = `url('${url}${cacheBusterUrl}')`;
    svgDentigrama.style.backgroundSize = 'contain'; 
    svgDentigrama.style.backgroundRepeat = 'no-repeat';
    svgDentigrama.style.backgroundPosition = 'center';
}

// === RENDERIZADO DEL SVG (Dientes) ===
function renderizarDentigrama() {
    // Limpiar lienzo previo
    while (svgDentigrama.firstChild) { svgDentigrama.removeChild(svgDentigrama.firstChild); }

    const startX = 30; const gap = 48;
    
    // Dibujar filas
    dientesAdultosSup.forEach((num, i) => { let x = startX + (i*gap); if(i>=8) x+=20; svgDentigrama.appendChild(crearDienteSVG(num, x, 50)); });
    
    const offsetNinos = (gap*3)+20; 
    dientesNinosSup.forEach((num, i) => { let x = startX + offsetNinos + (i*gap); if(i>=5) x+=20; svgDentigrama.appendChild(crearDienteSVG(num, x, 140)); });
    dientesNinosInf.forEach((num, i) => { let x = startX + offsetNinos + (i*gap); if(i>=5) x+=20; svgDentigrama.appendChild(crearDienteSVG(num, x, 220)); });
    
    dientesAdultosInf.forEach((num, i) => { let x = startX + (i*gap); if(i>=8) x+=20; svgDentigrama.appendChild(crearDienteSVG(num, x, 310)); });

    // Referencias L/R solo si es fondo blanco puro
    if (!tieneFondo) {
        agregarTexto(40, 400, "DERECHA", "start");
        agregarTexto(820, 400, "IZQUIERDA", "end");
    }
}

function crearDienteSVG(numero, x, y) {
    const grupo = document.createElementNS(SVG_NS, "g");
    grupo.setAttribute("class", "diente-group");
    grupo.setAttribute("transform", `translate(${x}, ${y})`);
    grupo.setAttribute("data-diente", numero);
    grupo.addEventListener('click', (e) => handleClickGlobal(e, grupo), true);

    // Si NO tiene fondo, dibujamos el número visible. Si tiene fondo, asumimos que la imagen ya lo trae.
    // (Opcional: puedes dejarlo siempre visible si prefieres)
    if (!tieneFondo) {
        const texto = document.createElementNS(SVG_NS, "text");
        texto.setAttribute("x", 25); texto.setAttribute("y", -8); 
        texto.setAttribute("class", "diente-numero"); 
        texto.textContent = numero; 
        grupo.appendChild(texto);
    }

    const zonasGroup = document.createElementNS(SVG_NS, "g");
    zonasGroup.setAttribute("class", "diente-zonas");

    // LÓGICA CRÍTICA DE VISIBILIDAD:
    // Si tiene fondo (historial), el relleno es TRANSPARENTE (para ver atrás).
    // Si es nuevo, el relleno es BLANCO (para tapar el fondo del canvas).
    const fillStyle = tieneFondo ? "transparent" : "white"; 
    const strokeStyle = tieneFondo ? "none" : "#333"; 
    
    // Si tiene fondo, usamos una clase especial .zona (definida en CSS con fill casi invisible)
    // Si no, pintamos explícitamente.
    const props = { fill: fillStyle, stroke: strokeStyle };

    crearZona(zonasGroup, "M10.8,10.8 L19.3,19.3 A8,8 0 0,1 30.7,19.3 L39.2,10.8 A20,20 0 0,0 10.8,10.8 Z", "vestibular", props);
    crearZona(zonasGroup, "M39.2,10.8 L30.7,19.3 A8,8 0 0,1 30.7,30.7 L39.2,39.2 A20,20 0 0,0 39.2,10.8 Z", "derecha", props);
    crearZona(zonasGroup, "M39.2,39.2 L30.7,30.7 A8,8 0 0,1 19.3,30.7 L10.8,39.2 A20,20 0 0,0 39.2,39.2 Z", "lingual", props);
    crearZona(zonasGroup, "M10.8,39.2 L19.3,30.7 A8,8 0 0,1 19.3,19.3 L10.8,10.8 A20,20 0 0,0 10.8,39.2 Z", "izquierda", props);
    
    const cCentro = document.createElementNS(SVG_NS, "circle");
    cCentro.setAttribute("cx", 25); cCentro.setAttribute("cy", 25); cCentro.setAttribute("r", 8); 
    cCentro.setAttribute("class", "zona"); 
    cCentro.setAttribute("data-cara", "oclusal"); 
    cCentro.setAttribute("fill", props.fill); 
    
    // Si no tiene fondo, necesita borde. Si tiene fondo, el borde estorba (a menos que se quiera).
    if(!tieneFondo) {
        cCentro.setAttribute("stroke", props.stroke); 
        cCentro.setAttribute("stroke-width", "1");
    }
    
    zonasGroup.appendChild(cCentro); 
    grupo.appendChild(zonasGroup);

    // Capas de Tratamientos (Ocultas por defecto)
    crearCapaX(grupo, "layer-extraccion", "#dc3545");
    crearCapaX(grupo, "layer-ausente", "#0d6efd"); // Azul para ausente según convención
    
    const endo = document.createElementNS(SVG_NS, "text");
    endo.setAttribute("class", "layer-structure layer-endo"); 
    endo.setAttribute("x", 25); endo.setAttribute("y", -20); 
    endo.setAttribute("text-anchor", "middle"); 
    endo.setAttribute("fill", "#d63384"); 
    endo.setAttribute("font-size", "10"); 
    endo.setAttribute("font-weight", "bold"); 
    endo.textContent = "ENDO"; 
    endo.setAttribute("display", "none"); 
    grupo.appendChild(endo);

    const protesis = document.createElementNS(SVG_NS, "g");
    protesis.setAttribute("class", "layer-structure layer-protesis"); 
    protesis.setAttribute("display", "none"); 
    crearLinea(protesis, 0, 15, 50, 15, "#0d6efd"); 
    crearLinea(protesis, 0, 35, 50, 35, "#0d6efd"); 
    grupo.appendChild(protesis);

    const corona = document.createElementNS(SVG_NS, "circle");
    corona.setAttribute("class", "layer-structure layer-corona"); 
    corona.setAttribute("cx", 25); corona.setAttribute("cy", 25); corona.setAttribute("r", 23); 
    corona.setAttribute("fill", "none"); 
    corona.setAttribute("stroke", "#0d6efd"); 
    corona.setAttribute("stroke-width", "3"); 
    corona.setAttribute("display", "none"); 
    grupo.appendChild(corona);
    
    const check = document.createElementNS(SVG_NS, "path");
    check.setAttribute("class", "layer-structure layer-check"); 
    check.setAttribute("d", "M8,25 L22,38 L44,12"); 
    check.setAttribute("fill", "none"); 
    check.setAttribute("stroke", "#6f42c1"); 
    check.setAttribute("stroke-width", "7"); 
    check.setAttribute("stroke-linecap", "round"); 
    check.setAttribute("stroke-linejoin", "round"); 
    check.setAttribute("display", "none"); 
    grupo.appendChild(check);

    return grupo;
}

// Helpers SVG
function crearZona(padre, d, cara, props) { 
    const path = document.createElementNS(SVG_NS, "path"); 
    path.setAttribute("d", d); 
    path.setAttribute("class", "zona"); 
    path.setAttribute("data-cara", cara); 
    path.setAttribute("fill", props.fill); 
    if(props.stroke !== 'none') {
        path.setAttribute("stroke", props.stroke); 
        path.setAttribute("stroke-width", "1"); 
    }
    padre.appendChild(path); 
}
function crearCapaX(grupo, clase, color) { const g = document.createElementNS(SVG_NS, "g"); g.setAttribute("class", `layer-structure ${clase}`); g.setAttribute("display", "none"); crearLinea(g, 5, 5, 45, 45, color, 4); crearLinea(g, 45, 5, 5, 45, color, 4); grupo.appendChild(g); }
function crearLinea(padre, x1, y1, x2, y2, color, width=3) { const l = document.createElementNS(SVG_NS, "line"); l.setAttribute("x1", x1); l.setAttribute("y1", y1); l.setAttribute("x2", x2); l.setAttribute("y2", y2); l.setAttribute("stroke", color); l.setAttribute("stroke-width", width); padre.appendChild(l); }
function agregarTexto(x, y, texto, anchor) { const t = document.createElementNS(SVG_NS, "text"); t.setAttribute("x", x); t.setAttribute("y", y); t.setAttribute("fill", "#aaa"); t.setAttribute("text-anchor", anchor); t.textContent = texto; svgDentigrama.appendChild(t); }


// === INTERACCIÓN ===
function setupHerramientas() { 
    window.setHerramienta = function(herramienta, btn) { 
        herramientaActual = herramienta; 
        document.querySelectorAll('.btn-tool').forEach(b => b.classList.remove('active')); 
        if(btn) btn.classList.add('active'); 
        logAction(`Herramienta: ${herramienta.toUpperCase()}`); 
    }; 
}

function handleClickGlobal(e, grupo) { 
    const globales = ['extraccion', 'ausente', 'endodoncia', 'protesis', 'borrador', 'corona', 'check']; 
    
    if (globales.includes(herramientaActual)) { 
        e.stopPropagation(); e.preventDefault(); 
        if (herramientaActual === 'borrador') limpiarDiente(grupo); 
        else aplicarEstado(grupo); 
        return; 
    } 
    
    if (e.target.classList.contains('zona')) pintarZona(e.target); 
}

function aplicarEstado(grupo) { 
    // Mapeo simple de herramienta a clase CSS
    const mapa = {
        'extraccion': '.layer-extraccion',
        'ausente': '.layer-ausente',
        'endodoncia': '.layer-endo',
        'protesis': '.layer-protesis',
        'corona': '.layer-corona',
        'check': '.layer-check'
    };
    
    const selector = mapa[herramientaActual];
    if(selector) toggle(grupo, selector);
    
    logAction(`Diente ${grupo.getAttribute('data-diente')}: ${herramientaActual.toUpperCase()}`); 
}

function toggle(grupo, sel) { 
    const el = grupo.querySelector(sel); 
    if(el) el.setAttribute('display', el.getAttribute('display') === 'none' ? 'block' : 'none'); 
}

function pintarZona(zona) { 
    zona.classList.remove('pintado-caries', 'pintado-amalgama', 'pintado-resina', 'pintado-blanco'); 
    
    if (herramientaActual === 'borrador') { 
        // Restaurar estado original
        zona.setAttribute('fill', tieneFondo ? 'transparent' : 'white'); 
        zona.removeAttribute('class'); 
        zona.setAttribute('class', 'zona'); 
        zona.style.fill = ""; 
        zona.style.opacity = ""; 
    } else { 
        let colorHex = '#ffffff'; 
        if(herramientaActual === 'caries') colorHex = '#dc3545'; 
        if(herramientaActual === 'amalgama') colorHex = '#0d6efd'; 
        if(herramientaActual === 'resina') colorHex = '#198754'; 
        
        zona.style.setProperty('fill', colorHex, 'important'); 
        zona.style.setProperty('opacity', '1', 'important'); 
        zona.style.setProperty('fill-opacity', '1', 'important'); 
        zona.classList.add(`pintado-${herramientaActual}`); 
    } 
    logAction(`Zona marcada: ${herramientaActual}`); 
}

function limpiarDiente(grupo) { 
    // Ocultar todas las capas estructurales
    grupo.querySelectorAll('.layer-structure').forEach(l => l.setAttribute('display', 'none'));
    
    // Limpiar zonas
    grupo.querySelectorAll('.zona').forEach(z => { 
        z.style.fill = ""; 
        z.style.opacity = ""; 
        z.setAttribute('fill', tieneFondo ? 'transparent' : 'white'); 
        z.classList.remove('pintado-caries', 'pintado-amalgama', 'pintado-resina'); 
    }); 
    logAction(`Diente restaurado.`); 
}

function logAction(mensaje) { 
    const logDiv = document.getElementById('debug-log'); 
    if (logDiv) { 
        logDiv.textContent = "Última acción: " + mensaje; 
        logDiv.style.color = "#0d6efd"; 
        setTimeout(() => logDiv.style.color = "", 300); 
    } 
}


// === FUNCIÓN DE EXPORTACIÓN V23.4 (SVG AUTO-REPARABLE) ===
// Si la imagen de fondo falla, convierte los dientes transparentes en visibles
// forzando bordes oscuros y relleno blanco.

window.svgToPng = function(svgElement) {
    return new Promise(async (resolve, reject) => {
        try {
            const width = 860;
            const height = 480;
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            // 1. PINTAR FONDO BLANCO BASE
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, width, height);

            let backgroundLoaded = false; // Bandera para saber si cargó el fondo

            // 2. INTENTAR CARGAR FONDO HISTÓRICO (Cloudinary)
            const inputUrl = document.getElementById('dentigrama_url_input');
            
            if (inputUrl && inputUrl.value && inputUrl.value.startsWith('http')) {
                try {
                    let secureUrl = inputUrl.value.replace(/^http:\/\//i, 'https://');
                    const cacheBuster = (secureUrl.indexOf('?') > -1 ? '&' : '?') + 't=' + new Date().getTime();
                    
                    const response = await fetch(secureUrl + cacheBuster, { 
                        mode: 'cors', cache: 'no-store' 
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const img = await createImageBitmap(blob);
                        ctx.drawImage(img, 0, 0, width, height);
                        backgroundLoaded = true; // ¡Éxito! Tenemos fondo real.
                    } else {
                        console.warn("⚠️ Imagen de fondo no encontrada (404). Se reconstruirá el dibujo.");
                    }
                } catch (err) {
                    console.warn("⚠️ Error cargando fondo:", err);
                }
            }

            // 3. PROCESAR EL SVG (AQUÍ ESTÁ LA MAGIA)
            const serializer = new XMLSerializer();
            let svgString = serializer.serializeToString(svgElement);
            
            // CORRECCIÓN CRÍTICA: "REVELADO DIGITAL"
            // Si NO cargó el fondo (backgroundLoaded === false), los dientes son invisibles.
            // Los forzamos a ser visibles modificando el texto del SVG.
            
            if (!backgroundLoaded) {
                console.log("🛠️ Reparando visualización: Pintando dientes...");
                
                // 1. Cambiar relleno transparente por blanco
                // Reemplaza todas las ocurrencias de fill="transparent"
                svgString = svgString.split('fill="transparent"').join('fill="#ffffff"');
                
                // 2. Cambiar sin borde por borde gris oscuro
                // Reemplaza stroke="none" por un color visible
                svgString = svgString.split('stroke="none"').join('stroke="#333333"');
                
                // 3. Asegurar grosor de línea si falta
                // Si por alguna razón el stroke-width es 0, lo ponemos a 1
                svgString = svgString.split('stroke-width="0"').join('stroke-width="1"');
            }

            // Ajuste de tamaño standard
            if(!svgElement.getAttribute('width')) {
                svgString = svgString.replace('<svg', `<svg width="${width}" height="${height}"`);
            }
            
            // 4. DIBUJAR EL SVG FINAL AL CANVAS
            const svgBlob = new Blob([svgString], {type: 'image/svg+xml;charset=utf-8'});
            const url = URL.createObjectURL(svgBlob);
            const svgImg = new Image();

            svgImg.onload = function() {
                ctx.drawImage(svgImg, 0, 0, width, height);
                const pngData = canvas.toDataURL('image/png');
                URL.revokeObjectURL(url);
                resolve(pngData);
            };
            
            svgImg.onerror = (e) => {
                URL.revokeObjectURL(url);
                reject(new Error("Error procesando los trazos del dentigrama."));
            };

            svgImg.src = url;

        } catch (e) {
            console.error("Error crítico exportando:", e);
            reject(e); 
        }
    });
};

// === GUARDADO MANUAL (BOTÓN PEQUEÑO DEL DENTIGRAMA) ===
function setupGuardadoManual() {
    const btnGuardar = document.getElementById('btnGuardarDentigrama');
    if(btnGuardar) {
        const newBtn = btnGuardar.cloneNode(true);
        btnGuardar.parentNode.replaceChild(newBtn, btnGuardar);

        newBtn.addEventListener('click', async function() {
            newBtn.disabled = true;
            newBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Procesando...';

            try {
                const base64Img = await window.svgToPng(svgDentigrama);

                const inputUrl = document.getElementById('dentigrama_url_input');
                if(inputUrl) inputUrl.value = base64Img;

                let patientId = document.getElementById('patientIdHiddenInput')?.value;
                let idToSend = "";

                if (patientId && patientId !== "None" && patientId.trim() !== "") {
                    idToSend = patientId;
                } else if (tempSessionId) {
                    idToSend = tempSessionId;
                }

                if (!idToSend && (!patientId || patientId === "None")) {
                    alert('Dentigrama preparado. Dale a "Registrar" para finalizar.');
                    newBtn.disabled = false;
                    newBtn.innerHTML = '💾 Guardar Cambios al Dentigrama';
                    return;
                }

                const response = await fetch('/pacientes/upload_dentigrama', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_data: base64Img, patient_id: idToSend }),
                });

                const data = await response.json();

                if (response.ok && (data.success || data.url)) {
                    if(data.url) {
                        inputUrl.value = data.url;

                        // ▼▼▼ SOLUCIÓN DUPLICADOS: Guardar el Public ID ▼▼▼
                        const publicIdInput = document.getElementById('dentigrama_public_id_input');
                        if (publicIdInput && data.public_id) {
                            publicIdInput.value = data.public_id;
                        }

                        // ▼▼▼ SOLUCIÓN EFECTO FANTASMA ▼▼▼
                        // 1. Actualizamos el estado: ahora SÍ tiene fondo
                        tieneFondo = true;
                        // 2. Re-renderizamos el SVG. Al ser tieneFondo=true,
                        // se dibujará SIN los textos ni números, evitando el dobleimpreso.
                        renderizarDentigrama();
                        // 3. Cargamos la nueva imagen como fondo visual
                        cargarFondoVisual(data.url);
                        // ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
                    }
                    alert('Dentigrama actualizado correctamente.');
                } else {
                    throw new Error(data.error || 'Error desconocido');
                }

            } catch (e) {
                console.error(e);
                alert('No se pudo guardar: ' + e.message);
            } finally {
                newBtn.disabled = false;
                newBtn.innerHTML = '💾 Guardar Cambios al Dentigrama';
            }
        });
    }
}