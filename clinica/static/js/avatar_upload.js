// static/js/avatar_upload.js

document.addEventListener('DOMContentLoaded', function () {
    console.log("Avatar Upload Script: DOMContentLoaded fired.");

    const profilePictureInput = document.getElementById('imagen_perfil_input');
    const profilePicturePreview = document.getElementById('profile-picture-preview');
    const cameraButton = document.querySelector('.avatar-actions .camera-btn');
    const uploadButton = document.querySelector('.avatar-actions .upload-btn');

    if (profilePictureInput && profilePicturePreview && cameraButton && uploadButton) {
        console.log("Avatar Upload Script: Elements found. Initializing listeners.");

        // Guardar la URL original del placeholder o imagen actual
        if (profilePicturePreview.src) {
            profilePicturePreview.dataset.originalSrc = profilePicturePreview.src;
        }

        // Función para actualizar la previsualización de la imagen
        profilePictureInput.addEventListener('change', function () {
            if (this.files && this.files[0]) {
                const file = this.files[0];
                
                // Validar que sea una imagen
                if (!file.type.startsWith('image/')) {
                    alert('Por favor, selecciona un archivo de imagen válido.');
                    this.value = ''; // Limpiar el input
                    profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
                    return;
                }
                
                // Validar tamaño (máximo 5MB)
                const maxSize = 5 * 1024 * 1024; // 5MB
                if (file.size > maxSize) {
                    alert('La imagen es demasiado grande. El tamaño máximo es 5MB.');
                    this.value = '';
                    profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
                    return;
                }
                
                const reader = new FileReader();
                reader.onload = function (e) {
                    profilePicturePreview.src = e.target.result;
                };
                reader.onerror = function () {
                    console.error("Avatar Upload Script: Error al leer el archivo de imagen.");
                    alert("Error al cargar la imagen. Por favor, intenta con otro archivo.");
                };
                reader.readAsDataURL(file);
            } else {
                // Si no se selecciona archivo, restaurar la imagen original
                profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
            }
        });

        // Al hacer clic en el botón de cámara
        cameraButton.addEventListener('click', function () {
            console.log("Avatar Upload Script: Camera button clicked.");
            // Establece el atributo 'capture' para sugerir el uso de la cámara
            profilePictureInput.setAttribute('capture', 'environment');
            profilePictureInput.click();
        });

        // Al hacer clic en el botón de subir
        uploadButton.addEventListener('click', function () {
            console.log("Avatar Upload Script: Upload button clicked.");
            // Remueve el atributo 'capture' para permitir la navegación de archivos
            profilePictureInput.removeAttribute('capture');
            profilePictureInput.click();
        });

        // Recrear iconos de Lucide si están disponibles
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
    let avatarZoomModal = null;
    if (typeof bootstrap !== 'undefined') {
        const modalEl = document.getElementById('avatarZoomModal');
        if (modalEl) {
            try {
                avatarZoomModal = new bootstrap.Modal(modalEl);
            } catch (error) {
                console.error("Avatar Upload Script: Error al inicializar el modal de Bootstrap:", error);
            }
        } else {
            console.warn("Avatar Upload Script: Modal element 'avatarZoomModal' not found in DOM.");
        }
    }
    const zoomedAvatarImage = document.getElementById('zoomedAvatarImage');

    if (profilePicturePreview && avatarZoomModal && zoomedAvatarImage) {
        profilePicturePreview.style.cursor = 'pointer';
        profilePicturePreview.addEventListener('click', function () {
            zoomedAvatarImage.src = this.src;
            avatarZoomModal.show();
            console.log("Avatar Upload Script: Avatar image clicked, showing zoom modal.");
        });
    } else {
        console.warn("Avatar Upload Script Warning: No se encontraron los elementos para la funcionalidad de zoom del avatar.");
    }

});