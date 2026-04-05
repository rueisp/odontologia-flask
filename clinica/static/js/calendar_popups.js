// static/js/calendar_popups.js
document.addEventListener("DOMContentLoaded", function() {
    const calendarContainer = document.querySelector(".calendar-container");

    // Si no hay contenedor de calendario en la página, no hacer nada.
    if (!calendarContainer) {
        return;
    }

    // Función para cerrar un popup específico
    function closePopup(popup) {
        if (popup) {
            popup.remove();
        }
    }

    // Función para cerrar todos los popups
    function closeAllPopups() {
        calendarContainer.querySelectorAll(".appointments-popup").forEach(popup => {
            popup.remove();
        });
    }

    // Usar delegación de eventos en el contenedor del calendario
    calendarContainer.addEventListener("click", function(event) {
        // Buscar si se hizo clic en el indicador de citas
        const indicator = event.target.closest(".appointment-indicator");
        
        // Buscar si se hizo clic en el botón cerrar del popup
        const closeButton = event.target.closest(".close-popup");

        if (indicator) {
            event.stopPropagation();
            
            // Obtener el día (la celda) que contiene el indicador
            const dayCell = indicator.closest('.day');
            if (!dayCell) return;
            
            // Buscar si ya hay un popup abierto en este día
            let existingPopup = dayCell.querySelector('.appointments-popup');
            
            if (existingPopup) {
                // Si ya existe, lo cerramos
                existingPopup.remove();
                return;
            }
            
            // Cerrar cualquier otro popup abierto
            closeAllPopups();
            
            // Obtener las citas almacenadas en el día
            let appointments = [];
            try {
                // Intentar obtener las citas del dataset del día
                if (dayCell.dataset.appointments) {
                    appointments = JSON.parse(dayCell.dataset.appointments);
                }
            } catch(e) {
                console.error("Error parsing appointments:", e);
            }
            
            if (appointments.length === 0) return;
            
            // Crear el popup
            const popup = document.createElement('div');
            popup.className = 'appointments-popup';
            
            let popupContent = '<h4>📋 Citas del día</h4>';
            
            for (let i = 0; i < appointments.length; i++) {
                const cita = appointments[i];
                const hora = cita.hora || '--:--';
                const nombre = cita.nombre || cita.paciente || 'Sin nombre';
                popupContent += `<div class="appointment-detail">${hora} - ${nombre}</div>`;
            }
            
            popupContent += '<button class="close-popup">✕ Cerrar</button>';
            popup.innerHTML = popupContent;
            
            dayCell.appendChild(popup);
            
            // Posicionar el popup
            const popupRect = popup.getBoundingClientRect();
            const dayRect = dayCell.getBoundingClientRect();
            
            // Ajuste horizontal
            if (popupRect.right > window.innerWidth - 10) {
                popup.style.left = 'auto';
                popup.style.right = '0';
            } else {
                popup.style.left = '0';
                popup.style.right = 'auto';
            }
            
            // Ajuste vertical (mostrar abajo)
            popup.style.top = (dayCell.offsetHeight + 5) + 'px';
            popup.style.bottom = 'auto';
            
            // Configurar el botón de cerrar
            const closeBtn = popup.querySelector('.close-popup');
            closeBtn.onclick = function(e) {
                e.stopPropagation();
                popup.remove();
            };
            
        } else if (closeButton) {
            event.stopPropagation();
            const popup = closeButton.closest(".appointments-popup");
            if (popup) {
                popup.remove();
            }
        }
    });

    // Clic fuera del popup para cerrarlo
    document.addEventListener("click", function(event) {
        const isInsidePopup = event.target.closest(".appointments-popup");
        const isIndicator = event.target.closest(".appointment-indicator");
        
        if (!isInsidePopup && !isIndicator && calendarContainer) {
            closeAllPopups();
        }
    });
});