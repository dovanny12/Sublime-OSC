# Sublime - Sistema Integrado

Este proyecto incluye un backend Python (Flask) que usa la base de datos de `BD` para iniciar sesión y registrar usuarios.

## Pasos para ejecutar

1. Abrir terminal en `Sublime`.
2. Ejecutar `pip install -r requirements.txt`.
3. Si quieres usar MySQL, configura estas variables de entorno antes de ejecutar:
   - `MYSQL_HOST`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_DATABASE`
4. Ejecutar `python server.py`.
5. Abrir `http://localhost:3000/login/index.html`.

## Cuenta de prueba

- Correo: `admin@sublime.com`
- Contraseña: `admin123`

## Qué se integró

- `login/index.html` y `login/script.js` usan `POST /api/login` y `POST /api/register`.
- `admin-panel/index.html` verifica sesión, permite cerrar sesión y carga datos reales.
- `server.py` usa `BD/database.db` si ya existe, o crea la base de datos desde `BD/database.sql`.
- El servidor expone endpoints para el dashboard, inventario, clientes, facturas y ventas.
- El sistema se puede abrir desde `http://localhost:3000/` y redirige al login, luego al admin-panel.
