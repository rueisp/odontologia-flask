document.addEventListener('DOMContentLoaded', function() {
    const btnDictado = document.getElementById('btn-dictado');
    const textarea = document.getElementById('evolucion-textarea');

    if (!btnDictado || !textarea) return;

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Tu navegador no permite dictado por voz. Asegúrate de usar Chrome o Safari y tener el candado de seguridad (HTTPS) activo.");
        return;
    }

    let recognition = null;
    let grabando = false;

    const DICCIONARIO_DENTAL = {
        "arcos de mi ti": "arcos de NiTi",
        "arco adenitis": "arcos de NiTi",
        "arcos de niti": "arcos de NiTi",
        "obturacion": "obturación",
        "obturaciones": "obturaciones",
        "mesiar": "mesial",
        "distar": "distal",
        "vestibular": "vestibular"
    };

    function aplicarCorrecciones(texto) {
        let textoFinal = texto.trim();
        for (const [error, correccion] of Object.entries(DICCIONARIO_DENTAL)) {
            const regex = new RegExp("\\b" + error + "\\b", "gi");
            textoFinal = textoFinal.replace(regex, correccion);
        }
        return textoFinal.charAt(0).toUpperCase() + textoFinal.slice(1);
    }

    function detenerGrabacion() {
        if (recognition) {
            recognition.stop();
            recognition = null;
        }
        grabando = false;
        btnDictado.classList.remove('recording');
    }

    function iniciarGrabacion() {
        // Creamos una instancia nueva cada vez para Safari
        recognition = new SpeechRecognition();
        recognition.lang = 'es-CO';
        recognition.continuous = false;
        recognition.interimResults = false;

        recognition.onstart = () => {
            grabando = true;
            btnDictado.classList.add('recording');
        };

        recognition.onresult = (event) => {
            if (event.results.length > 0) {
                const transcriptRaw = event.results[0][0].transcript;
                const corregido = aplicarCorrecciones(transcriptRaw);
                const current = textarea.value.trim();
                
                textarea.value = current + (current ? ' ' : '') + corregido + '.';
                // Disparar evento para que Flask/JS sepa que hay texto
                textarea.dispatchEvent(new Event('change'));
                textarea.dispatchEvent(new Event('input'));
            }
        };

        recognition.onerror = (e) => {
            console.error("Error Speech API:", e.error);
            detenerGrabacion();
        };

        recognition.onend = () => {
            detenerGrabacion();
        };

        recognition.start();
    }

    btnDictado.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();

        if (grabando) {
            detenerGrabacion();
        } else {
            iniciarGrabacion();
        }
    });
});