// static/js/avatar_upload.js

document.addEventListener('DOMContentLoaded', function() {
    console.log("Avatar Upload Script: DOMContentLoaded fired.");

    const profilePictureInput = document.getElementById('imagen_perfil_input');
    const profilePicturePreview = document.getElementById('profile-picture-preview');
    const cameraButton = document.querySelector('.avatar-actions .camera-btn');
    const uploadButton = document.querySelector('.avatar-actions .upload-btn');

    if (profilePictureInput && profilePicturePreview && cameraButton && uploadButton) {
        console.log("Avatar Upload Script: Elements found. Initializing listeners.");

        // Guardar la URL original del placeholder o imagen actual
        // Para que si el usuario cancela la selección, se mantenga la imagen original.
        // Solo para 'registrar_paciente.html' esta será el placeholder.
        // Para 'editar_paciente.html' podría ser la imagen existente del paciente.
        profilePicturePreview.dataset.originalSrc = profilePicturePreview.src;

        // Función para actualizar la previsualización de la imagen
        profilePictureInput.addEventListener('change', function() {
            if (this.files && this.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    profilePicturePreview.src = e.target.result;
                };
                reader.readAsDataURL(this.files[0]);
            } else {
                // Si no se selecciona ningún archivo o se cancela, restaurar la imagen existente o el placeholder
                profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
            }
        });

        // Al hacer clic en el botón de cámara
        cameraButton.addEventListener('click', function() {
            console.log("Avatar Upload Script: Camera button clicked.");
            // Establece el atributo 'capture' para sugerir el uso de la cámara
            profilePictureInput.setAttribute('capture', 'environment');
            profilePictureInput.click(); // Abre el selector de archivos/cámara
        });

        // Al hacer clic en el botón de subir
        uploadButton.addEventListener('click', function() {
            console.log("Avatar Upload Script: Upload button clicked.");
            // Remueve el atributo 'capture' para permitir la navegación de archivos
            profilePictureInput.removeAttribute('capture');
            profilePictureInput.click(); // Abre el selector de archivos
        });
        
        // Es importante volver a crear los iconos de Lucide si se han añadido nuevos elementos con data-lucide
        // Si tu script principal ya llama a lucide.createIcons() después del DOMContentLoaded,
        // puedes omitir esta línea si los elementos ya existen en el DOM al cargar.
        // Pero si los elementos se añaden dinámicamente o por un include, puede ser necesario.
        if (typeof lucide !== 'undefined' && lucide.createIcons) {
             lucide.createIcons();
             console.log("Avatar Upload Script: Lucide icons re-created for new buttons.");
        } else {
            console.warn("Avatar Upload Script: Lucide library not found or createIcons not available.");
        }

    } else {
        console.warn("Avatar Upload Script Warning: No se encontraron todos los elementos para la carga de imagen de perfil.");
    }

    // --- Lógica para Ampliar Imagen de Perfil ---
    const avatarZoomModal = new bootstrap.Modal(document.getElementById('avatarZoomModal'));
    const zoomedAvatarImage = document.getElementById('zoomedAvatarImage');

    if (profilePicturePreview && avatarZoomModal && zoomedAvatarImage) {
        profilePicturePreview.style.cursor = 'pointer'; // Para indicar que es clickeable
        profilePicturePreview.addEventListener('click', function() {
            zoomedAvatarImage.src = this.src; // Establece la fuente de la imagen ampliada a la fuente actual del avatar
            avatarZoomModal.show(); // Muestra el modal
            console.log("Avatar Upload Script: Avatar image clicked, showing zoom modal.");
        });
    } else {
        console.warn("Avatar Upload Script Warning: No se encontraron los elementos para la funcionalidad de zoom del avatar.");
    }

});