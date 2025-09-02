// Archivo: clinica/static/js/editor_dentigrama.js
// VERSIÓN CORREGIDA Y CON TAMAÑO DE CHECK AJUSTADO

document.addEventListener('DOMContentLoaded', function() {

    const canvas = document.getElementById('dentigrama_canvas');
    if (!canvas) {
        console.warn("No se encontró el canvas 'dentigrama_canvas' en esta página.");
        return;
    }

    const ctx = canvas.getContext('2d');
    const dentigramaUrlInput = document.getElementById('dentigrama_canvas_input');

    // --- Variables de estado unificadas ---
    let modoActual = 'pincel'; // 'pincel', 'check'
    let colorPincel = 'red'; 
    let grosorPincel = 5; 
    let dibujando = false;
    let ultimoX = 0;
    let ultimoY = 0;

    // Historial de acciones
    let historial = [];

    // --- Utilidades ---
    // Obtiene las coordenadas del mouse/touch relativas y escaladas
    const getCoords = (e) => {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        let clientX = e.clientX, clientY = e.clientY;
        if (e.touches && e.touches.length) {
            clientX = e.touches[0].clientX;
            clientY = e.touches[0].clientY;
        }
        return { x: (clientX - rect.left) * scaleX, y: (clientY - rect.top) * scaleY };
    };

    // --- Funciones de Dibujo ---

    // Dibuja el check de forma vectorial
    function dibujarCheckVectorial(ctx, x, y, size = 25, color = 'purple', lineWidth = 8) {
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

    // Redibuja todo el canvas desde el historial
    function redibujarTodo() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        const dentigramaImg = document.getElementById('dentigrama_img_src');
        if (dentigramaImg && dentigramaImg.src) {
            const img = new Image();
            img.src = dentigramaImg.src;
            img.crossOrigin = "Anonymous";
            img.onload = () => {
                canvas.width = img.width;
                canvas.height = img.height;
                canvas.style.width = img.width + 'px';
                canvas.style.height = img.height + 'px';
                ctx.drawImage(img, 0, 0);
                redibujarAcciones();
            };
        } else {
            redibujarAcciones(); // ← Aquí se asegura que los trazos se dibujen aunque no haya imagen
        }
    }

    function redibujarAcciones() {
    historial.forEach(accion => {
        if (accion.tipo === 'linea') {
            ctx.strokeStyle = accion.color;
            ctx.lineWidth = accion.grosor;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.beginPath();
            ctx.moveTo(accion.x1 * canvas.width, accion.y1 * canvas.height);
            ctx.lineTo(accion.x2 * canvas.width, accion.y2 * canvas.height);
            ctx.stroke();
        } else if (accion.tipo === 'check') {
            dibujarCheckVectorial(
                ctx,
                accion.x * canvas.width,
                accion.y * canvas.height,
                accion.size,
                accion.color,
                accion.grosor
            );
        }
    });
}

    // --- Eventos de mouse y touch unificados ---
    canvas.addEventListener('mousedown', (e) => {
        const { x, y } = getCoords(e);
        
        if (modoActual === 'pincel') {
            dibujando = true;
            ultimoX = x / canvas.width;
            ultimoY = y / canvas.height;
        } else if (modoActual === 'check') {
            // Guardar el check en el historial con el nuevo tamaño y grosor
            historial.push({
                tipo: 'check',
                x: x / canvas.width,
                y: y / canvas.height,
                size: 25, // ¡Valores ajustados aquí!
                color: 'purple',
                grosor: 8 // ¡Valores ajustados aquí!
            });
            redibujarTodo();
            modoActual = 'pincel';
        }
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!dibujando || modoActual !== 'pincel') return;
        const { x, y } = getCoords(e);

        historial.push({
            tipo: 'linea',
            x1: ultimoX,
            y1: ultimoY,
            x2: x / canvas.width,
            y2: y / canvas.height,
            color: colorPincel,
            grosor: grosorPincel
        });
        redibujarTodo();
        ultimoX = x / canvas.width;
        ultimoY = y / canvas.height;
    });
    
    canvas.addEventListener('mouseup', () => {
        dibujando = false;
    });

    canvas.addEventListener('mouseout', () => {
        dibujando = false;
    });
    
    // --- Funciones para la Botonera ---
    window.cambiarColor = function(color) {
        colorPincel = color;
        modoActual = 'pincel';
    };

    window.activarCheck = function() {
        modoActual = 'check';
    };

    window.limpiarCanvas = function() {
        historial = [];
        redibujarTodo();
    };

    window.deshacer = function() {
        if (historial.length > 0) {
            historial.pop();
            redibujarTodo();
        }
    };

    window.guardarImagen = function() {
        redibujarTodo(); // ← asegura que todo esté sincronizado

        setTimeout(() => {
            const dataURL = canvas.toDataURL('image/png');
            document.getElementById('dentigrama_url_input').value = dataURL;
            alert("Dentigrama actualizado. No olvides guardar los cambios del formulario.");
        }, 100); // ← da tiempo al navegador para aplicar el layout
    };

    // Asignación de event listeners a los botones
    document.getElementById('btnColorRojo')?.addEventListener('click', () => cambiarColor('red'));
    document.getElementById('btnColorAzul')?.addEventListener('click', () => cambiarColor('blue'));
    document.getElementById('btnColorNegro')?.addEventListener('click', () => cambiarColor('black'));
    document.getElementById('btnActivarCheck')?.addEventListener('click', activarCheck);
    document.getElementById('btnLimpiar')?.addEventListener('click', limpiarCanvas);
    document.getElementById('btnDeshacer')?.addEventListener('click', deshacer); // Se añade la función de deshacer
    document.getElementById('btnGuardarDentigrama')?.addEventListener('click', guardarImagen);

    // Inicialización del canvas
    redibujarTodo();
});