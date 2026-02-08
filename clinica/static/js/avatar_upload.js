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
                        
                        // 1. Validar que sea una imagen O PDF
                        const isImage = file.type.startsWith('image/');
                        const isPdf = file.type === 'application/pdf';
                        const isImageOrPdf = isImage || isPdf;
                        
                        if (!isImageOrPdf) {
                            alert('Por favor, selecciona un archivo de imagen o PDF válido.');
                            this.value = '';
                            profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
                            return;
                        }
                        
                        // 2. Validar tamaño (máximo 5MB)
                        const maxSize = 5 * 1024 * 1024; // 5MB
                        if (file.size > maxSize) {
                            alert('El archivo es demasiado grande. El tamaño máximo es 5MB.');
                            this.value = '';
                            profilePicturePreview.src = profilePicturePreview.dataset.originalSrc;
                            return;
                        }

                        // 3. MANEJO DE PREVISUALIZACIÓN (SOLO SI ES IMAGEN)
                        if (isImage) {
                            const reader = new FileReader();
                            reader.onload = function (e) {
                                profilePicturePreview.src = e.target.result;
                            };
                            reader.onerror = function () {
                                console.error("Avatar Upload Script: Error al leer el archivo de imagen.");
                                alert("Error al cargar la imagen. Por favor, intenta con otro archivo.");
                            };
                            reader.readAsDataURL(file);
                        } else if (isPdf) {
                            // --- FEEDBACK VISUAL PARA PDF ---
                            console.log("PDF seleccionado. Mostrando ícono de PDF.");
                            
                            // Creamos un ícono de PDF básico usando SVG directamente en código (no necesitas descargar imágenes)
                            const svgPdfIcon = "data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120' viewBox='0 0 24 24' fill='none' stroke='%23333' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/%3E%3Cpolyline points='14 2 14 8 20 8'/%3E%3Ctext x='5.5' y='16' font-size='6' font-family='Arial' stroke='none' fill='%23dc3545' font-weight='bold'%3EPDF%3C/text%3E%3C/svg%3E";
                            
                            profilePicturePreview.src = svgPdfIcon;
                        }

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

    // COMENTAR/ELIMINAR ESTE BLOQUE:
/*
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
            zoomedAvatarImage.src = this.src; // Este src es el ícono de PDF
            avatarZoomModal.show();
            console.log("Avatar Upload Script: Avatar image clicked, showing zoom modal.");
        });
    } else {
        console.warn("Avatar Upload Script Warning: No se encontraron los elementos para la funcionalidad de zoom del avatar.");
    }
*/
// ...

});