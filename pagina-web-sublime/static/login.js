document.addEventListener('DOMContentLoaded', () => {
    const formLogin = document.getElementById('formLogin');
    const mensajeError = document.getElementById('mensajeError');

    if (formLogin) {
        formLogin.addEventListener('submit', async (evento) => {
            evento.preventDefault();

            const usuarioInput = document.getElementById('usuario').value.trim();
            const contrasenaInput = document.getElementById('password').value;
            const nextInput = document.querySelector('input[name="next"]');
            const nextRedirect = nextInput ? nextInput.value : '';

            mensajeError.style.display = 'none';
            mensajeError.textContent = '';

            try {
                const respuesta = await fetch('/api/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        usuario: usuarioInput,
                        contrasena: contrasenaInput
                    })
                });

                const datos = await respuesta.json();

                if (respuesta.ok) {
                    localStorage.setItem('sesionActiva', 'true');
                    localStorage.setItem('nombreUsuario', usuarioInput);
                    window.location.href = nextRedirect || '/';
                } else {
                    mensajeError.textContent = datos.mensaje || 'El usuario o la contraseña no son correctos. Inténtalo de nuevo.';
                    mensajeError.style.display = 'block';
                }

            } catch (error) {
                console.error(error);
                mensajeError.textContent = 'Hubo un problema de conexión. Revisa tu internet.';
                mensajeError.style.display = 'block';
            }
        });
    }
});
