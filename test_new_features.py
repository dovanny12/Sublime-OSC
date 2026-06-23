"""
test_new_features.py
Pruebas de integración para la funcionalidad de cuentas vinculadas (linked accounts).
Cubre:
  1. Esquema de base de datos – tabla cuentas_vinculadas
  2. Inicio de sesión con Google (login/registro automático + vinculación)
  3. Inicio de sesión con Facebook (login/registro automático + vinculación)
  4. Rutas de vinculación desde el perfil (link_mode)
  5. Ruta de desvinculación /perfil/desvincular/<proveedor>
  6. Vista de perfil con cuentas vinculadas (linked_accounts en template)
"""

import os
import sys
import sqlite3
import tempfile
import shutil
import unittest

# ---------------------------------------------------------------------------
# Ajustar sys.path para que Python encuentre app.py en este directorio
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Crear un directorio temporal persistente para toda la suite de tests
# ---------------------------------------------------------------------------
_TEMP_DIR = tempfile.mkdtemp(prefix="sublime_test_")
_TEMP_DB = os.path.join(_TEMP_DIR, "database.db")
_ORIG_SQL = os.path.abspath(
    os.path.join(BASE_DIR, "..", "Sublime", "BD", "database.sql")
)

# ---------------------------------------------------------------------------
# Parchear las rutas de BD ANTES de importar la app
# ---------------------------------------------------------------------------
import app as app_module

app_module.SHARED_DB_PATH = _TEMP_DB
app_module.SHARED_SQL_PATH = _ORIG_SQL

from app import app

app.config["TESTING"] = True
app.config["SECRET_KEY"] = "test_secret"


# ---------------------------------------------------------------------------
# Utilidades compartidas
# ---------------------------------------------------------------------------

def _get_conn():
    """Conexión directa a la BD temporal."""
    conn = sqlite3.connect(_TEMP_DB)
    conn.row_factory = sqlite3.Row
    return conn


def _reset_db():
    """Recrea la BD temporal desde el esquema SQL original con datos mínimos."""
    if os.path.exists(_TEMP_DB):
        os.remove(_TEMP_DB)
    conn = sqlite3.connect(_TEMP_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    if os.path.exists(_ORIG_SQL):
        with open(_ORIG_SQL, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
    conn.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('Administrador')")
    conn.execute("INSERT OR IGNORE INTO roles (nombre) VALUES ('Trabajador')")
    conn.execute(
        "INSERT OR IGNORE INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)",
        ("testuser", "test@example.com", "secret123", 2),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Clase base con reset por método
# ---------------------------------------------------------------------------

class BaseLinkedAccountsTest(unittest.TestCase):
    """Resetea la BD completa antes de cada test para garantizar aislamiento."""

    def setUp(self):
        _reset_db()
        self.client = app.test_client()

    def tearDown(self):
        pass  # La BD se resetea en setUp del siguiente test

    def _login(self, client=None):
        """Inicia sesión con el usuario de prueba."""
        c = client or self.client
        c.post(
            "/login",
            data={"username": "test@example.com", "password": "secret123"},
            follow_redirects=True,
        )

    def _link_provider(self, provider, provider_id, email="test@example.com", client=None):
        """Vincula una cuenta de proveedor estando autenticado."""
        c = client or self.client
        c.get(
            f"/login/{provider}",
            query_string={"link": "true", "email": email, "provider_id": provider_id, "username": "testuser"},
        )


# ===========================================================================
# 1. Esquema de base de datos
# ===========================================================================

class TestDBSchema(BaseLinkedAccountsTest):
    """Verifica que la tabla cuentas_vinculadas existe con las columnas correctas."""

    def test_table_exists(self):
        """La tabla cuentas_vinculadas debe existir en la BD."""
        conn = _get_conn()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cuentas_vinculadas'"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(row, "La tabla 'cuentas_vinculadas' no fue encontrada.")

    def test_columns_present(self):
        """La tabla debe tener todas las columnas requeridas."""
        conn = _get_conn()
        cols = {col["name"] for col in conn.execute("PRAGMA table_info(cuentas_vinculadas)").fetchall()}
        conn.close()
        required = {"id_vinculacion", "id_usuario", "proveedor", "proveedor_id", "proveedor_correo", "fecha_vinculacion"}
        self.assertTrue(required.issubset(cols), f"Columnas faltantes: {required - cols}")

    def test_unique_constraint_provider_id(self):
        """No se puede insertar el mismo proveedor_id dos veces para el mismo proveedor."""
        conn = _get_conn()
        uid = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'test@example.com' LIMIT 1"
        ).fetchone()["id_usuario"]
        conn.execute(
            "INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, 'google', 'g_unique_1', 'a@b.com')",
            (uid,),
        )
        conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, 'google', 'g_unique_1', 'a@b.com')",
                (uid,),
            )
            conn.commit()
        conn.close()

    def test_unique_constraint_user_provider(self):
        """Un usuario no puede tener dos vinculaciones del mismo proveedor."""
        conn = _get_conn()
        uid = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'test@example.com' LIMIT 1"
        ).fetchone()["id_usuario"]
        conn.execute(
            "INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, 'facebook', 'fb_a', 'a@b.com')",
            (uid,),
        )
        conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, 'facebook', 'fb_b', 'a@b.com')",
                (uid,),
            )
            conn.commit()
        conn.close()


# ===========================================================================
# 2. Login con Google
# ===========================================================================

class TestGoogleLogin(BaseLinkedAccountsTest):
    """Inicio de sesión y vinculación automática con Google."""

    def test_google_login_creates_new_user(self):
        """Login de Google con correo nuevo crea un usuario y redirige."""
        r = self.client.get(
            "/login/google",
            query_string={"username": "NuevoGoogle", "email": "nuevo_google@gmail.com", "provider_id": "google_new_001"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302], "Debe redirigir tras el login de Google.")
        conn = _get_conn()
        user = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'nuevo_google@gmail.com' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(user, "El usuario de Google no fue creado en la BD.")

    def test_google_login_links_existing_user_by_email(self):
        """Login de Google con correo existente vincula al usuario existente."""
        r = self.client.get(
            "/login/google",
            query_string={"username": "testuser", "email": "test@example.com", "provider_id": "google_exist_002"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302])
        conn = _get_conn()
        link = conn.execute(
            "SELECT id_usuario FROM cuentas_vinculadas WHERE proveedor = 'google' AND proveedor_id = 'google_exist_002' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(link, "La cuenta de Google no fue vinculada al usuario existente.")

    def test_google_login_repeated_provider_id_no_duplicate(self):
        """El mismo provider_id de Google no genera vinculaciones duplicadas."""
        self.client.get(
            "/login/google",
            query_string={"username": "RepeatGoogle", "email": "repeat@gmail.com", "provider_id": "google_repeat_003"},
        )
        self.client.get(
            "/login/google",
            query_string={"username": "RepeatGoogle", "email": "repeat@gmail.com", "provider_id": "google_repeat_003"},
            follow_redirects=False,
        )
        conn = _get_conn()
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM cuentas_vinculadas WHERE proveedor = 'google' AND proveedor_id = 'google_repeat_003'"
        ).fetchone()["c"]
        conn.close()
        self.assertEqual(count, 1, "No debe haber vinculaciones duplicadas.")


# ===========================================================================
# 3. Login con Facebook
# ===========================================================================

class TestFacebookLogin(BaseLinkedAccountsTest):
    """Inicio de sesión y vinculación automática con Facebook."""

    def test_facebook_login_creates_new_user(self):
        """Login de Facebook con correo nuevo crea un usuario."""
        r = self.client.get(
            "/login/facebook",
            query_string={"username": "NuevoFB", "email": "nuevo_fb@facebook.com", "provider_id": "fb_new_001"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302])
        conn = _get_conn()
        user = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'nuevo_fb@facebook.com' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(user)

    def test_facebook_login_links_existing_user_by_email(self):
        """Login de Facebook con correo existente vincula al usuario existente."""
        r = self.client.get(
            "/login/facebook",
            query_string={"username": "testuser", "email": "test@example.com", "provider_id": "fb_exist_002"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302])
        conn = _get_conn()
        link = conn.execute(
            "SELECT id_usuario FROM cuentas_vinculadas WHERE proveedor = 'facebook' AND proveedor_id = 'fb_exist_002' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(link)

    def test_facebook_login_repeated_provider_id_no_duplicate(self):
        """El mismo provider_id de Facebook no genera vinculaciones duplicadas."""
        for _ in range(2):
            self.client.get(
                "/login/facebook",
                query_string={"username": "RepeatFB", "email": "repeat_fb@gmail.com", "provider_id": "fb_repeat_003"},
            )
        conn = _get_conn()
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM cuentas_vinculadas WHERE proveedor = 'facebook' AND proveedor_id = 'fb_repeat_003'"
        ).fetchone()["c"]
        conn.close()
        self.assertEqual(count, 1)


# ===========================================================================
# 4. Rutas de vinculación (link_mode)
# ===========================================================================

class TestLinkingRoutes(BaseLinkedAccountsTest):
    """Vinculación de cuentas desde el perfil cuando el usuario ya está autenticado."""

    def test_link_google_while_authenticated(self):
        """Un usuario autenticado puede vincular una cuenta de Google."""
        self._login()
        r = self.client.get(
            "/login/google",
            query_string={"link": "true", "username": "testuser", "email": "test@example.com", "provider_id": "google_link_001"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("perfil", r.headers.get("Location", ""), "Debe redirigir al perfil.")
        conn = _get_conn()
        link = conn.execute(
            "SELECT proveedor_id FROM cuentas_vinculadas WHERE proveedor = 'google' AND proveedor_id = 'google_link_001' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(link, "La vinculación de Google no fue registrada.")

    def test_link_facebook_while_authenticated(self):
        """Un usuario autenticado puede vincular una cuenta de Facebook."""
        self._login()
        r = self.client.get(
            "/login/facebook",
            query_string={"link": "true", "username": "testuser", "email": "test@example.com", "provider_id": "fb_link_001"},
            follow_redirects=False,
        )
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("perfil", r.headers.get("Location", ""))
        conn = _get_conn()
        link = conn.execute(
            "SELECT proveedor_id FROM cuentas_vinculadas WHERE proveedor = 'facebook' AND proveedor_id = 'fb_link_001' LIMIT 1"
        ).fetchone()
        conn.close()
        self.assertIsNotNone(link)

    def test_link_duplicate_google_same_user(self):
        """Vincular la misma cuenta de Google por segunda vez no crea duplicados."""
        self._login()
        self._link_provider("google", "google_dup_001")
        # Segunda vez
        self.client.get(
            "/login/google",
            query_string={"link": "true", "email": "test@example.com", "provider_id": "google_dup_001"},
            follow_redirects=True,
        )
        conn = _get_conn()
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM cuentas_vinculadas WHERE proveedor = 'google' AND proveedor_id = 'google_dup_001'"
        ).fetchone()["c"]
        conn.close()
        self.assertEqual(count, 1, "No deben existir vinculaciones duplicadas.")


# ===========================================================================
# 5. Ruta de desvinculación
# ===========================================================================

class TestUnlinkRoute(BaseLinkedAccountsTest):
    """Ruta POST /perfil/desvincular/<proveedor>."""

    def test_unlink_google_with_password(self):
        """Un usuario con contraseña propia puede desvincular Google."""
        self._login()
        self._link_provider("google", "google_unlink_001")
        r = self.client.post("/perfil/desvincular/google", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = _get_conn()
        uid = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'test@example.com' LIMIT 1"
        ).fetchone()["id_usuario"]
        link = conn.execute(
            "SELECT id_vinculacion FROM cuentas_vinculadas WHERE id_usuario = ? AND proveedor = 'google' LIMIT 1",
            (uid,),
        ).fetchone()
        conn.close()
        self.assertIsNone(link, "La vinculación de Google debería haberse eliminado.")

    def test_unlink_facebook_with_password(self):
        """Un usuario con contraseña propia puede desvincular Facebook."""
        self._login()
        self._link_provider("facebook", "fb_unlink_001")
        r = self.client.post("/perfil/desvincular/facebook", follow_redirects=True)
        self.assertEqual(r.status_code, 200)
        conn = _get_conn()
        uid = conn.execute(
            "SELECT id_usuario FROM usuarios WHERE correo = 'test@example.com' LIMIT 1"
        ).fetchone()["id_usuario"]
        link = conn.execute(
            "SELECT id_vinculacion FROM cuentas_vinculadas WHERE id_usuario = ? AND proveedor = 'facebook' LIMIT 1",
            (uid,),
        ).fetchone()
        conn.close()
        self.assertIsNone(link)

    def test_unlink_requires_login(self):
        """Sin sesión activa, la desvinculación debe redirigir al login."""
        r = self.client.post("/perfil/desvincular/google", follow_redirects=False)
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("login", r.headers.get("Location", ""), "Debe redirigir al login.")

    def test_unlink_invalid_provider(self):
        """Un proveedor inválido debe redirigir al perfil sin errores de servidor."""
        self._login()
        r = self.client.post("/perfil/desvincular/twitter", follow_redirects=True)
        self.assertEqual(r.status_code, 200, "No debe devolver 5xx.")

    def test_unlink_oauth_only_account_blocked(self):
        """Un usuario sin contraseña real no puede desvincular su único proveedor."""
        # Crear usuario solo con OAuth
        conn = _get_conn()
        cursor = conn.execute(
            "INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)",
            ("OAuthOnly", "oauth_only@gmail.com", "oauth_simulated", 2),
        )
        oauth_uid = cursor.lastrowid
        conn.execute(
            "INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, 'google', 'g_oauth_only', 'oauth_only@gmail.com')",
            (oauth_uid,),
        )
        conn.commit()
        conn.close()

        # Iniciar sesión como ese usuario vía Google
        self.client.get(
            "/login/google",
            query_string={"email": "oauth_only@gmail.com", "provider_id": "g_oauth_only", "username": "OAuthOnly"},
            follow_redirects=True,
        )
        self.client.post("/perfil/desvincular/google", follow_redirects=True)

        # La vinculación NO debe haberse borrado
        conn = _get_conn()
        link = conn.execute(
            "SELECT id_vinculacion FROM cuentas_vinculadas WHERE id_usuario = ? AND proveedor = 'google' LIMIT 1",
            (oauth_uid,),
        ).fetchone()
        conn.close()
        self.assertIsNotNone(link, "La vinculación no debe eliminarse si es el único método de acceso.")


# ===========================================================================
# 6. Interfaz de usuario – perfil con cuentas vinculadas
# ===========================================================================

class TestProfileLinkedAccountsUI(BaseLinkedAccountsTest):
    """Verifica que el template perfil.html muestra correctamente las cuentas vinculadas."""

    def test_profile_requires_authentication(self):
        """El perfil redirige al login si no hay sesión."""
        r = self.client.get("/perfil", follow_redirects=False)
        self.assertIn(r.status_code, [301, 302])
        self.assertIn("login", r.headers.get("Location", ""))

    def test_profile_shows_no_linked_accounts(self):
        """Sin cuentas vinculadas, el perfil muestra 'No vinculada' para ambos proveedores."""
        self._login()
        r = self.client.get("/perfil")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("No vinculada", html, "'No vinculada' no aparece en el perfil.")

    def test_profile_shows_linked_google_email(self):
        """Tras vincular Google, el correo de la cuenta aparece en el perfil."""
        self._login()
        self._link_provider("google", "g_ui_001", email="mi_google@gmail.com")
        r = self.client.get("/perfil")
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        self.assertIn("mi_google@gmail.com", html, "El correo de Google no aparece en el perfil.")

    def test_profile_shows_desvincular_button_when_linked(self):
        """Con cuenta vinculada, el botón 'Desvincular' debe aparecer."""
        self._login()
        self._link_provider("facebook", "fb_ui_001")
        r = self.client.get("/perfil")
        html = r.get_data(as_text=True)
        self.assertIn("Desvincular", html, "El botón Desvincular no aparece.")
        self.assertIn("desvincular/facebook", html, "La ruta de desvinculación de Facebook no aparece en el formulario.")

    def test_profile_shows_vincular_button_when_not_linked(self):
        """Sin cuenta vinculada, el botón 'Vincular' debe aparecer."""
        self._login()
        r = self.client.get("/perfil")
        html = r.get_data(as_text=True)
        self.assertIn("Vincular", html, "El botón Vincular no aparece cuando no hay cuentas vinculadas.")

    def test_profile_section_exists(self):
        """La sección 'Cuentas Vinculadas' debe existir en el perfil."""
        self._login()
        r = self.client.get("/perfil")
        html = r.get_data(as_text=True)
        self.assertIn("Cuentas Vinculadas", html)
        self.assertIn("Google", html)
        self.assertIn("Facebook", html)

    def test_profile_shows_linked_facebook_email(self):
        """Tras vincular Facebook, el correo de esa cuenta aparece en el perfil."""
        self._login()
        self._link_provider("facebook", "fb_ui_002", email="mi_fb@facebook.com")
        r = self.client.get("/perfil")
        html = r.get_data(as_text=True)
        self.assertIn("mi_fb@facebook.com", html, "El correo de Facebook no aparece en el perfil.")


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  Pruebas de integración – Cuentas Vinculadas (Sublime)")
    print("=" * 60)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestDBSchema,
        TestGoogleLogin,
        TestFacebookLogin,
        TestLinkingRoutes,
        TestUnlinkRoute,
        TestProfileLinkedAccountsUI,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Limpiar directorio temporal
    try:
        shutil.rmtree(_TEMP_DIR, ignore_errors=True)
    except Exception:
        pass

    sys.exit(0 if result.wasSuccessful() else 1)
