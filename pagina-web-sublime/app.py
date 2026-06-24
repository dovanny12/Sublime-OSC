import os
import time
import json
import uuid
import sqlite3
import urllib.request
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from functools import wraps
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import db, User, Product, Order

app = Flask(__name__)
CORS(app)
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")
app.secret_key = os.environ.get('SECRET_KEY', 'super_secret_key_for_sublime')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
if os.environ.get('ENFORCE_HTTPS', '').lower() in ('1', 'true', 'yes'):
    app.config['SESSION_COOKIE_SECURE'] = True

def is_safe_url(target):
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024

def validate_image_file(file_storage):
    if not file_storage or not file_storage.filename:
        return False
    ext = file_storage.filename.rsplit('.', 1)[-1].lower() if '.' in file_storage.filename else ''
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_IMAGE_SIZE:
        return False
    return True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_default_db = os.path.abspath(os.path.join(BASE_DIR, '..', 'Sublime', 'BD', 'database.db'))
SHARED_DB_PATH = os.environ.get('DATABASE_PATH', _default_db)
SHARED_SQL_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'Sublime', 'BD', 'database.sql'))
ADMIN_PANEL_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'Sublime', 'admin-panel'))

# OAuth Configuration (set these via environment variables or .env)
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_APP_SECRET = os.environ.get('FACEBOOK_APP_SECRET', '')

def get_base_url():
    return os.environ.get('OAUTH_REDIRECT_BASE', 'http://localhost:5000')

from urllib.parse import urlencode

def google_oauth_url(state=''):
    params = {
        'client_id': GOOGLE_CLIENT_ID,
        'redirect_uri': f'{get_base_url()}/auth/google/callback',
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'offline'
    }
    if state:
        params['state'] = state
    return f'https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}'

def facebook_oauth_url(state=''):
    params = {
        'client_id': FACEBOOK_APP_ID,
        'redirect_uri': f'{get_base_url()}/auth/facebook/callback',
        'response_type': 'code',
        'scope': 'email'
    }
    if state:
        params['state'] = state
    return f'https://www.facebook.com/v19.0/dialog/oauth?{urlencode(params)}'

def exchange_google_code(code):
    data = urlencode({
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': f'{get_base_url()}/auth/google/callback',
        'grant_type': 'authorization_code'
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read().decode())
    access_token = token_data['access_token']
    req2 = urllib.request.Request(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    with urllib.request.urlopen(req2) as resp2:
        return json.loads(resp2.read().decode())

def exchange_facebook_code(code):
    params = urlencode({
        'client_id': FACEBOOK_APP_ID,
        'client_secret': FACEBOOK_APP_SECRET,
        'redirect_uri': f'{get_base_url()}/auth/facebook/callback',
        'code': code
    })
    req = urllib.request.Request(f'https://graph.facebook.com/v19.0/oauth/access_token?{params}')
    with urllib.request.urlopen(req) as resp:
        token_data = json.loads(resp.read().decode())
    access_token = token_data['access_token']
    req2 = urllib.request.Request(f'https://graph.facebook.com/me?fields=id,name,email&access_token={access_token}')
    with urllib.request.urlopen(req2) as resp2:
        return json.loads(resp2.read().decode())

# Cache para la tasa BCV
BCV_CACHE = {'usd': 40.0, 'eur': 45.0, 'updated': 0}
CACHE_TTL = 3600  # 1 hora

def get_config_rate():
    try:
        conn = sqlite3.connect(SHARED_DB_PATH)
        conn.row_factory = sqlite3.Row
        row = conn.execute('SELECT tasa_usd, tasa_eur FROM configuracion LIMIT 1').fetchone()
        conn.close()
        if row and row['tasa_usd'] and float(row['tasa_usd']) > 0:
            return float(row['tasa_usd']), float(row['tasa_eur'] or 0) if row['tasa_eur'] else 0
    except Exception:
        pass
    return None, None

def save_config_rate(usd, eur):
    try:
        conn = sqlite3.connect(SHARED_DB_PATH)
        existing = conn.execute('SELECT id_configuracion FROM configuracion LIMIT 1').fetchone()
        if existing:
            conn.execute('UPDATE configuracion SET tasa_usd = ?, tasa_eur = ? WHERE id_configuracion = ?', (usd, eur, existing[0]))
        else:
            conn.execute('INSERT INTO configuracion (tasa_usd, tasa_eur) VALUES (?, ?)', (usd, eur))
        conn.commit()
        conn.close()
    except Exception:
        pass

def fetch_bcv_rates(force=False):
    now = time.time()
    if not force and now - BCV_CACHE['updated'] < CACHE_TTL:
        return BCV_CACHE['usd'], BCV_CACHE['eur']
    try:
        req = urllib.request.Request(
            'https://rates.dolarvzla.com/bcv/current.json',
            headers={'User-Agent': 'SublimeApp/1.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            usd = float(data['current']['usd'])
            eur = float(data['current']['eur'])
            if usd > 0 and eur > 0:
                BCV_CACHE['usd'] = usd
                BCV_CACHE['eur'] = eur
                BCV_CACHE['updated'] = now
                save_config_rate(usd, eur)
    except Exception:
        pass
    return BCV_CACHE['usd'], BCV_CACHE['eur']

def get_active_rate():
    usd_db, eur_db = get_config_rate()
    if usd_db and usd_db > 0:
        return usd_db, eur_db, 'manual'
    usd_bcv, eur_bcv = fetch_bcv_rates()
    return usd_bcv, eur_bcv, 'bcv'

def fetch_bcv_rate():
    usd, _, _ = get_active_rate()
    return usd

# =========================================================
# IVA helpers
# =========================================================
IVA_CACHE = {'rate': 16.0, 'updated': 0}

def get_config_iva():
    try:
        conn = sqlite3.connect(SHARED_DB_PATH)
        row = conn.execute('SELECT iva_default FROM configuracion LIMIT 1').fetchone()
        conn.close()
        if row and row[0] is not None and float(row[0]) > 0:
            return float(row[0])
    except Exception:
        pass
    return None

def save_config_iva(rate):
    try:
        conn = sqlite3.connect(SHARED_DB_PATH)
        existing = conn.execute('SELECT id_configuracion FROM configuracion LIMIT 1').fetchone()
        if existing:
            conn.execute('UPDATE configuracion SET iva_default = ? WHERE id_configuracion = ?', (rate, existing[0]))
        else:
            conn.execute('INSERT INTO configuracion (iva_default) VALUES (?)', (rate,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_iva_rate():
    iva = get_config_iva()
    if iva and iva > 0:
        IVA_CACHE['rate'] = iva
        IVA_CACHE['updated'] = time.time()
        return iva
    return IVA_CACHE['rate']

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{SHARED_DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
os.makedirs(os.path.dirname(SHARED_DB_PATH), exist_ok=True)


def ensure_shared_db():
    conn = sqlite3.connect(SHARED_DB_PATH)
    conn.execute('PRAGMA foreign_keys = ON')
    if os.path.exists(SHARED_SQL_PATH):
        with open(SHARED_SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        # Split into individual statements and execute each one
        for statement in sql.split(';'):
            stmt = statement.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception:
                    pass
    conn.commit()
    conn.close()


def get_shared_db():
    ensure_shared_db()
    conn = sqlite3.connect(SHARED_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def is_panel_admin():
    return session.get('user_role') in ('Administrador Panel', 'Administrador')


def require_panel_admin():
    if 'user_id' not in session or not is_panel_admin():
        return False
    return True

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not require_panel_admin():
            return jsonify({'message': 'Acceso no autorizado.'}), 401
        return f(*args, **kwargs)
    return decorated


def seed_default_admin():
    ensure_shared_db()
    conn = sqlite3.connect(SHARED_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        conn.execute('INSERT OR IGNORE INTO roles (id_rol, nombre) VALUES (?, ?)', (1, 'Administrador Panel'))
        conn.execute('INSERT OR IGNORE INTO roles (id_rol, nombre) VALUES (?, ?)', (2, 'Trabajador'))
        conn.execute('INSERT OR IGNORE INTO roles (id_rol, nombre) VALUES (?, ?)', (3, 'Administrador Web'))
        conn.commit()

        panel_admin = conn.execute('SELECT id_usuario, id_rol FROM usuarios WHERE correo = ? LIMIT 1', ('admin@sublime.com',)).fetchone()
        if not panel_admin:
            conn.execute(
                'INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)',
                ('Administrador Panel', 'admin@sublime.com', generate_password_hash('admin123'), 1)
            )
            conn.commit()
        elif panel_admin['id_rol'] != 1:
            conn.execute('UPDATE usuarios SET id_rol = ? WHERE id_usuario = ?', (1, panel_admin['id_usuario']))
            conn.commit()

        web_admin = conn.execute('SELECT id_usuario, id_rol FROM usuarios WHERE correo = ? LIMIT 1', ('admin_web@sublime.com',)).fetchone()
        if not web_admin:
            conn.execute(
                'INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)',
                ('Administrador Web', 'admin_web@sublime.com', generate_password_hash('adminweb123'), 3)
            )
            conn.commit()
        elif web_admin['id_rol'] != 3:
            conn.execute('UPDATE usuarios SET id_rol = ? WHERE id_usuario = ?', (3, web_admin['id_usuario']))
            conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


CATEGORIES = ['camisas', 'tazas', 'gorras', 'llaveros', 'termos/filtros', 'mousepads', 'bolígrafos']


def validate_stock(conn, product_id, quantity=1):
    if not product_id:
        return True, None
    row = conn.execute(
        'SELECT IFNULL(stock_actual, 0) AS stock FROM inventario WHERE id_producto = ?',
        (product_id,)
    ).fetchone()
    stock = row['stock'] if row else 0
    if stock < quantity:
        name_row = conn.execute('SELECT nombre FROM productos WHERE id_producto = ?', (product_id,)).fetchone()
        name = name_row['nombre'] if name_row else 'Producto'
        return False, f'"{name}" no tiene stock suficiente. Disponible: {stock}'
    return True, None


def placeholder():
    return '?'


def map_product_row(row):
    return {
        'id': row['id_producto'],
        'name': row['nombre'],
        'category': row['categoria'] or 'General',
        'price': float(row['precio_venta']),
        'image_url': row['ruta_imagen'] or 'placeholder.png',
        'description': row['descripcion'] or '',
        'stock': row['stock'] if 'stock' in row else 0
    }


seed_default_admin()

def fetch_products(categoria=None, search_query=None, sort_option='newest', limit=None):
    conn = get_shared_db()
    sql = (
        'SELECT p.id_producto, p.nombre, p.descripcion, p.precio_venta, '
        'c.nombre AS categoria, '
        'COALESCE((SELECT ruta_imagen FROM imagenes_productos ip WHERE ip.id_producto = p.id_producto ORDER BY ip.id_imagen LIMIT 1), ?) AS ruta_imagen '
        'FROM productos p '
        'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'WHERE p.activo = 1 AND p.id_categoria IS NOT NULL '
    )
    params = ['placeholder.png']

    if categoria:
        sql += ' AND c.nombre = ? '
        params.append(categoria)

    if search_query:
        sql += ' AND (p.nombre LIKE ? OR p.descripcion LIKE ?) '
        term = f'%{search_query}%'
        params.extend([term, term])

    if sort_option == 'price_asc':
        sql += ' ORDER BY p.precio_venta ASC '
    elif sort_option == 'price_desc':
        sql += ' ORDER BY p.precio_venta DESC '
    elif sort_option == 'name_asc':
        sql += ' ORDER BY p.nombre ASC '
    else:
        sql += ' ORDER BY p.id_producto DESC '

    if limit:
        sql += ' LIMIT ? '
        params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [map_product_row(row) for row in rows]


def fetch_product_by_id(product_id):
    conn = get_shared_db()
    row = conn.execute(
        'SELECT p.id_producto, p.nombre, p.descripcion, p.precio_venta, c.nombre AS categoria, '
        'COALESCE((SELECT ruta_imagen FROM imagenes_productos ip WHERE ip.id_producto = p.id_producto ORDER BY ip.id_imagen LIMIT 1), ?) AS ruta_imagen, '
        'IFNULL(i.stock_actual, 0) AS stock '
        'FROM productos p '
        'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.activo = 1 AND p.id_producto = ? ',
        ['placeholder.png', product_id]
    ).fetchone()
    conn.close()
    return map_product_row(row) if row else None


def get_or_create_client(conn, email, nombre, direccion, telefono='', cedula=''):
    if email:
        cliente = conn.execute('SELECT id_cliente FROM clientes WHERE correo = ? LIMIT 1', (email,)).fetchone()
        if cliente:
            conn.execute('UPDATE clientes SET telefono = ?, cedula = ? WHERE id_cliente = ?', (telefono, cedula, cliente['id_cliente']))
            conn.commit()
            return cliente['id_cliente']

    cliente = conn.execute('SELECT id_cliente FROM clientes WHERE nombre = ? AND direccion = ? LIMIT 1', (nombre, direccion)).fetchone()
    if cliente:
        return cliente['id_cliente']

    cursor = conn.execute(
        'INSERT INTO clientes (nombre, correo, telefono, direccion, cedula) VALUES (?, ?, ?, ?, ?)',
        (nombre, email, telefono, direccion, cedula)
    )
    conn.commit()
    return cursor.lastrowid


def ensure_order_statuses(conn):
    count = conn.execute('SELECT COUNT(*) AS total FROM estados_pedido').fetchone()['total']
    if count == 0:
        conn.executemany('INSERT INTO estados_pedido (nombre) VALUES (?)', [('Pendiente',), ('Procesando',), ('Enviado',), ('Entregado',)])
        conn.commit()


def get_or_create_cart(conn, cliente_id):
    carrito = conn.execute('SELECT id_carrito FROM carrito WHERE id_cliente = ? AND fecha_creacion >= datetime("now", "-1 day") ORDER BY fecha_creacion DESC LIMIT 1', (cliente_id,)).fetchone()
    if carrito:
        return carrito['id_carrito']
    
    cursor = conn.execute('INSERT INTO carrito (id_cliente) VALUES (?)', (cliente_id,))
    conn.commit()
    return cursor.lastrowid


def get_or_create_custom_product(conn, name='Producto Personalizado', description='Producto personalizado', price=30.0):
    import time
    unique_name = f"{name} - {int(time.time()*1000)}"
    cat = conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', ('Personalizado',)).fetchone()
    if cat:
        cat_id = cat['id_categoria']
    else:
        cur = conn.execute('INSERT INTO categorias (nombre) VALUES (?)', ('Personalizado',))
        cat_id = cur.lastrowid
    cursor = conn.execute(
        'INSERT INTO productos (nombre, descripcion, costo, precio_venta, id_categoria, activo) VALUES (?, ?, ?, ?, ?, 1)',
        (unique_name, description, price, price, cat_id)
    )
    conn.commit()
    return cursor.lastrowid


def load_cart_from_db():
    if 'user_id' not in session:
        return []
    
    conn = get_shared_db()
    cliente_id = session['user_id']
    carrito_id = get_or_create_cart(conn, cliente_id)
    
    items = conn.execute(
        'SELECT dc.id_detalle, dc.id_producto, dc.cantidad, dc.precio_unitario, p.nombre AS name, p.descripcion, '
        '(SELECT ip.ruta_imagen FROM imagenes_productos ip WHERE ip.id_producto = p.id_producto ORDER BY ip.id_imagen LIMIT 1) AS image_url '
        'FROM detalle_carrito dc '
        'LEFT JOIN productos p ON dc.id_producto = p.id_producto '
        'WHERE dc.id_carrito = ? '
        'ORDER BY dc.id_detalle ASC',
        (carrito_id,)
    ).fetchall()
    conn.close()
    
    return [
        {
            'id': item['id_producto'],
            'name': item['name'] or 'Producto personalizado',
            'price': float(item['precio_unitario']),
            'quantity': item['cantidad'],
            'details': item['descripcion'] or '',
            'image_url': item['image_url'] or 'placeholder.png'
        }
        for item in items
    ]


def save_cart_to_db(cart_items):
    if 'user_id' not in session:
        return
    
    conn = get_shared_db()
    cliente_id = session['user_id']
    carrito_id = get_or_create_cart(conn, cliente_id)
    
    # Limpiar carrito anterior
    conn.execute('DELETE FROM detalle_carrito WHERE id_carrito = ?', (carrito_id,))
    
    # Insertar nuevos items
    for item in cart_items:
        conn.execute(
            'INSERT INTO detalle_carrito (id_carrito, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (carrito_id, item.get('id'), item.get('quantity', 1), item['price'])
        )
    
    conn.commit()
    conn.close()


def get_cart_count():
    return len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))


def load_current_user():
    if 'user_id' not in session:
        return None
    conn = get_shared_db()
    row = conn.execute(
        'SELECT id_usuario, nombre, correo, telefono FROM usuarios WHERE id_usuario = ? LIMIT 1',
        (session['user_id'],)
    ).fetchone()
    conn.close()
    if not row:
        return None

    return {
        'id': row['id_usuario'],
        'username': row['nombre'],
        'email': row['correo'],
        'phone': row['telefono'] or ''
    }


def merge_guest_cart_into_db(guest_cart):
    if 'user_id' not in session or not guest_cart:
        return
    if not isinstance(guest_cart, list):
        return

    db_cart = load_cart_from_db()
    for item in guest_cart:
        if not isinstance(item, dict):
            continue
        item_id = item.get('id')
        quantity = item.get('quantity', 1)
        price = item.get('price', 0)
        if item_id is None:
            continue

        existing = next((ci for ci in db_cart if ci.get('id') == item_id), None)
        if existing:
            existing['quantity'] = existing.get('quantity', 1) + quantity
        else:
            db_cart.append({
                'id': item_id,
                'name': item.get('name', 'Producto'),
                'price': price,
                'quantity': quantity,
                'details': item.get('details', '')
            })

    save_cart_to_db(db_cart)
    session.pop('cart', None)
    session.modified = True


# Configurar SQLAlchemy y asegurar existencia de la DB compartida.
db.init_app(app)
ensure_shared_db()

# Si creamos una DB vacía, permitir que SQLAlchemy cree las tablas definidas en models.py
with app.app_context():
    try:
        db.create_all()
    except Exception:
        # Ignorar errores aquí; la app seguirá intentando usar la DB compartida mediante sqlite3 directo
        pass

@app.context_processor
def inject_exchange_rate():
    tasa_usd, tasa_eur, fuente = get_active_rate()
    def format_price(usd_val):
        if usd_val is None:
            usd_val = 0.0
        try:
            usd_val = float(usd_val)
        except ValueError:
            usd_val = 0.0
        bs_val = usd_val * tasa_usd
        formatted_usd = f"${usd_val:,.2f}"
        formatted_bs = f"{bs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted_usd} / {formatted_bs} Bs"

    return dict(
        tasa_cambio=tasa_usd,
        format_price=format_price,
        cart_count=get_cart_count(),
        current_username=session.get('username'),
        iva_rate=get_iva_rate()
    )


@app.route('/api/tasa-cambio', methods=['GET', 'POST'])
def api_tasa_cambio():
    if request.method == 'POST':
        if not require_panel_admin():
            return jsonify({'mensaje': 'Acceso no autorizado.'}), 401
        data = request.get_json(silent=True) or {}
        usd = data.get('usd')
        eur = data.get('eur')
        if not usd or float(usd) <= 0:
            return jsonify({'mensaje': 'Tasa USD inválida'}), 400
        save_config_rate(float(usd), float(eur or 0))
        return jsonify({'mensaje': 'Tasa guardada correctamente', 'usd': float(usd), 'eur': float(eur or 0)})
    tasa_usd, tasa_eur, fuente = get_active_rate()
    return jsonify({'tasa': tasa_usd, 'usd': tasa_usd, 'eur': tasa_eur, 'fuente': fuente})


@app.route('/api/tasa-cambio/bcv')
def api_tasa_cambio_bcv():
    usd, eur = fetch_bcv_rates(force=True)
    return jsonify({'usd': usd, 'eur': eur, 'fuente': 'bcv', 'fecha': time.strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/api/config/iva', methods=['GET', 'POST'])
def api_config_iva():
    if request.method == 'POST':
        if not require_panel_admin():
            return jsonify({'mensaje': 'Acceso no autorizado.'}), 401
        data = request.get_json()
        rate = data.get('iva', 16.0)
        save_config_iva(float(rate))
        IVA_CACHE['rate'] = float(rate)
        IVA_CACHE['updated'] = time.time()
        return jsonify({'success': True, 'iva': float(rate)})
    return jsonify({'iva': get_iva_rate()})


@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def api_login():
    data = request.get_json(silent=True) or {}
    usuario = data.get('usuario', '').strip()
    contrasena = data.get('contrasena', '')

    if not usuario or not contrasena:
        return jsonify({'mensaje': 'Usuario y contraseña son requeridos.'}), 400

    conn = get_shared_db()
    user = conn.execute(
        'SELECT u.id_usuario, u.nombre, u.correo, u.contraseña, r.nombre AS rol '
        'FROM usuarios u LEFT JOIN roles r ON u.id_rol = r.id_rol '
        'WHERE u.correo = ? OR u.nombre = ? LIMIT 1',
        (usuario, usuario)
    ).fetchone()
    conn.close()

    if not user or not check_password_hash(user['contraseña'], contrasena):
        return jsonify({'mensaje': 'Credenciales inválidas.'}), 401

    session.clear()
    session['user_id'] = user['id_usuario']
    session['username'] = user['nombre']
    session['user_email'] = user['correo']
    session['user_role'] = user['rol'] or 'Trabajador'

    return jsonify({
        'mensaje': 'Inicio de sesión exitoso.',
        'usuario': {
            'id': user['id_usuario'],
            'nombre': user['nombre'],
            'correo': user['correo'],
            'rol': session['user_role']
        }
    })


@app.route('/api/products', methods=['GET'])
def api_products():
    categoria = request.args.get('categoria')
    q = request.args.get('q')
    sort = request.args.get('sort', 'newest')
    limit = request.args.get('limit')

    try:
        limit_value = int(limit) if limit else None
    except ValueError:
        limit_value = None

    products = fetch_products(categoria=categoria, search_query=q, sort_option=sort, limit=limit_value)
    return jsonify({'productos': products})


@app.route('/api/product/<int:product_id>', methods=['GET'])
def api_product(product_id):
    conn = get_shared_db()
    product = conn.execute(
        'SELECT p.id_producto, p.nombre, p.descripcion, p.precio_venta AS precio, '
        'c.nombre AS categoria, IFNULL(i.stock_actual, 0) AS stock, '
        'COALESCE((SELECT ruta_imagen FROM imagenes_productos WHERE id_producto = p.id_producto LIMIT 1), \'\') AS imagen '
        'FROM productos p '
        'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.id_producto = ?',
        (product_id,)
    ).fetchone()
    conn.close()
    if not product:
        return jsonify({'message': 'Producto no encontrado.'}), 404
    return jsonify({'product': dict(product)})


def get_cliente_id_by_session():
    if 'user_email' not in session:
        return None
    conn = get_shared_db()
    row = conn.execute(
        'SELECT id_cliente FROM clientes WHERE correo = ? LIMIT 1',
        (session['user_email'],)
    ).fetchone()
    conn.close()
    return row['id_cliente'] if row else None


@app.route('/api/orders', methods=['GET'])
def api_orders():
    if 'user_id' not in session:
        return jsonify({'mensaje': 'Necesitas iniciar sesión para ver tus pedidos.'}), 401

    cliente_id = get_cliente_id_by_session()
    if not cliente_id:
        return jsonify({'pedidos': []})

    conn = get_shared_db()
    rows = conn.execute(
        'SELECT p.id_pedido AS id, p.fecha, p.total, e.nombre AS estado, env.empresa_envio AS empresa_envio, env.numero_guia AS numero_guia '
        'FROM pedidos p '
        'LEFT JOIN estados_pedido e ON p.id_estado = e.id_estado '
        'LEFT JOIN envios env ON env.id_pedido = p.id_pedido '
        'WHERE p.id_cliente = ? '
        'ORDER BY p.fecha DESC',
        (cliente_id,)
    ).fetchall()
    conn.close()

    pedidos = [
        {
            'id': row['id'],
            'fecha': row['fecha'],
            'total': float(row['total'] or 0),
            'estado': row['estado'] or 'Pendiente',
            'empresa_envio': row['empresa_envio'] or '',
            'numero_guia': row['numero_guia'] or ''
        }
        for row in rows
    ]

    return jsonify({'pedidos': pedidos})


@app.route('/api/order/<int:order_id>', methods=['GET'])
def api_order_detail(order_id):
    if 'user_id' not in session:
        return jsonify({'mensaje': 'Necesitas iniciar sesión para ver este pedido.'}), 401

    cliente_id = get_cliente_id_by_session()
    if not cliente_id:
        return jsonify({'mensaje': 'No se encontró el cliente asociado.'}), 404

    conn = get_shared_db()
    order = conn.execute(
        'SELECT p.id_pedido AS id, p.fecha, p.total, e.nombre AS estado, c.nombre AS cliente, c.correo AS cliente_correo, '
        'env.direccion_envio AS direccion, env.empresa_envio AS empresa_envio, env.metodo_pago AS payment_method, env.referencia_pago AS reference, env.tipo_envio AS tipo_envio '
        'FROM pedidos p '
        'LEFT JOIN estados_pedido e ON p.id_estado = e.id_estado '
        'LEFT JOIN clientes c ON p.id_cliente = c.id_cliente '
        'LEFT JOIN envios env ON env.id_pedido = p.id_pedido '
        'WHERE p.id_pedido = ? AND p.id_cliente = ? LIMIT 1',
        (order_id, cliente_id)
    ).fetchone()

    if not order:
        conn.close()
        return jsonify({'mensaje': 'Pedido no encontrado.'}), 404

    items = conn.execute(
        'SELECT dp.id_detalle AS id, dp.id_producto AS product_id, pr.nombre AS name, dp.cantidad AS quantity, dp.precio_unitario AS price '
        'FROM detalle_pedidos dp '
        'LEFT JOIN productos pr ON dp.id_producto = pr.id_producto '
        'WHERE dp.id_pedido = ?',
        (order_id,)
    ).fetchall()
    conn.close()

    items_list = [
        {
            'id': item['id'],
            'product_id': item['product_id'],
            'name': item['name'] or 'Producto personalizado',
            'quantity': item['quantity'],
            'price': float(item['price'] or 0),
            'total': float((item['price'] or 0) * (item['quantity'] or 1))
        }
        for item in items
    ]

    pedido = {
        'id': order['id'],
        'fecha': order['fecha'],
        'total': float(order['total'] or 0),
        'estado': order['estado'] or 'Pendiente',
        'cliente': order['cliente'] or '',
        'cliente_correo': order['cliente_correo'] or '',
        'direccion': order['direccion'] or '',
        'payment_method': order['payment_method'] or '',
        'reference': order['reference'] or ''
    }

    return jsonify({'pedido': pedido, 'items': items_list})


@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per minute")
def api_register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not username or not email or not password:
        return jsonify({'mensaje': 'Nombre, correo y contraseña son requeridos.'}), 400

    conn = get_shared_db()
    existing = conn.execute(
        'SELECT id_usuario FROM usuarios WHERE nombre = ? OR correo = ? LIMIT 1',
        (username, email)
    ).fetchone()
    if existing:
        conn.close()
        return jsonify({'mensaje': 'El nombre de usuario o correo ya está en uso.'}), 409

    role = conn.execute('SELECT id_rol FROM roles WHERE nombre = ? LIMIT 1', ('Trabajador',)).fetchone()
    role_id = role['id_rol'] if role else 2
    conn.execute(
        'INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)',
        (username, email, generate_password_hash(password), role_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'mensaje': 'Registro exitoso. Ya puedes iniciar sesión.'}), 201


def calculate_cart_total(cart_items):
    return sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in cart_items)


@app.route('/api/cart', methods=['GET'])
def api_get_cart():
    if 'user_id' in session:
        cart = load_cart_from_db()
    else:
        cart = session.get('cart', [])

    total = calculate_cart_total(cart)
    return jsonify({'cart': cart, 'total': total})


@app.route('/api/cart', methods=['POST'])
def api_post_cart():
    data = request.get_json(silent=True) or {}
    items = data.get('items')

    if not isinstance(items, list):
        return jsonify({'mensaje': 'La lista de artículos es requerida.'}), 400

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        prod_id = item.get('id') or item.get('id_producto')
        if prod_id is None:
            continue
        try:
            prod_id = int(prod_id)
            quantity = max(1, int(item.get('quantity', 1)))
            price = float(item.get('price', 0))
        except (ValueError, TypeError):
            continue
        normalized.append({
            'id': prod_id,
            'name': item.get('name', ''),
            'details': item.get('details', ''),
            'price': price,
            'quantity': quantity
        })

    if 'user_id' in session:
        save_cart_to_db(normalized)
    else:
        session['cart'] = normalized
        session.modified = True

    total = calculate_cart_total(normalized)
    return jsonify({'mensaje': 'Carrito actualizado correctamente.', 'cart': normalized, 'total': total})


@app.route('/api/cart/add', methods=['POST'])
def api_add_to_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get('product_id')
    size = data.get('size', 'M')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'mensaje': 'ID de producto requerido.'}), 400

    try:
        product_id = int(product_id)
        quantity = max(1, int(quantity))
    except (ValueError, TypeError):
        return jsonify({'mensaje': 'Datos inválidos.'}), 400

    p = fetch_product_by_id(product_id)
    if not p:
        return jsonify({'mensaje': 'Producto no encontrado.'}), 404

    conn = get_shared_db()
    valid, msg = validate_stock(conn, product_id, quantity)
    conn.close()
    if not valid:
        return jsonify({'mensaje': msg}), 400

    cart = load_cart_from_db() if 'user_id' in session else session.get('cart', [])
    if not isinstance(cart, list):
        cart = []
    
    existing = next((item for item in cart if item.get('id') == product_id), None)
    if existing:
        existing['quantity'] += quantity
    else:
        cart.append({
            'id': p['id'], 
            'name': p['name'], 
            'price': p['price'], 
            'quantity': quantity,
            'size': size
        })
    
    if 'user_id' in session:
        save_cart_to_db(cart)
    else:
        session['cart'] = cart
        session.modified = True

    cart_count = len(cart)
    return jsonify({'mensaje': 'Producto añadido al carrito.', 'cart_count': cart_count})


@app.route('/api/checkout', methods=['POST'])
def api_checkout():
    data = request.get_json(silent=True) or {}

    if 'user_id' in session:
        cart_items = load_cart_from_db()
        user_name = session.get('username')
        user_email = session.get('user_email')
    else:
        cart_items = session.get('cart', [])
        user_name = data.get('name', '').strip()
        user_email = data.get('email', '').strip()

    if not isinstance(cart_items, list) or len(cart_items) == 0:
        return jsonify({'mensaje': 'El carrito está vacío.'}), 400

    address = data.get('address', '').strip()
    payment_method = data.get('payment_method', '').strip()
    reference = data.get('reference', '').strip()

    if not user_name or not address:
        return jsonify({'mensaje': 'Nombre y dirección son requeridos.'}), 400

    conn = get_shared_db()
    ensure_order_statuses(conn)

    # Validar stock antes de continuar
    for item in cart_items:
        product_id = item.get('id')
        if product_id and product_id != 0:
            cantidad = max(1, int(item.get('quantity', 1)))
            valid, msg = validate_stock(conn, product_id, cantidad)
            if not valid:
                conn.close()
                return jsonify({'mensaje': msg}), 400

    cliente_id = get_or_create_client(conn, user_email, user_name, address)
    status = conn.execute('SELECT id_estado FROM estados_pedido WHERE nombre = ? LIMIT 1', ('Pendiente',)).fetchone()
    status_id = status['id_estado'] if status else 1

    total = calculate_cart_total(cart_items)
    iva_rate = get_iva_rate()
    impuesto = round(total * iva_rate / 100, 2)
    total_con_iva = round(total + impuesto, 2)
    pedido_cursor = conn.execute(
        'INSERT INTO pedidos (id_cliente, id_estado, total) VALUES (?, ?, ?)',
        (cliente_id, status_id, total_con_iva)
    )
    pedido_id = pedido_cursor.lastrowid

    for item in cart_items:
        product_id = item.get('id')
        if not product_id or product_id == 0:
            product_id = get_or_create_custom_product(conn)
        cantidad = max(1, int(item.get('quantity', 1)))
        precio_unitario = float(item.get('price', 0))
        conn.execute(
            'INSERT INTO detalle_pedidos (id_pedido, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (pedido_id, product_id, cantidad, precio_unitario)
        )

    conn.execute(
        'INSERT INTO envios (id_pedido, direccion_envio, empresa_envio, numero_guia, estado_envio, fecha_envio, metodo_pago, referencia_pago, tipo_envio) VALUES (?, ?, ?, ?, ?, datetime("now"), ?, ?, ?)',
        (pedido_id, address, 'Pendiente', '', 'Pendiente', payment_method or 'Pendiente', reference or '', 'destino')
    )

    # También crear registro en ventas / detalle_ventas para que aparezca en Facturas del admin
    venta_cursor = conn.execute(
        'INSERT INTO ventas (id_cliente, total) VALUES (?, ?)',
        (cliente_id, total_con_iva)
    )
    venta_id = venta_cursor.lastrowid
    for item in cart_items:
        product_id = item.get('id')
        if not product_id or product_id == 0:
            product_id = get_or_create_custom_product(conn)
        cantidad = max(1, int(item.get('quantity', 1)))
        precio_unitario = float(item.get('price', 0))
        conn.execute(
            'INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (venta_id, product_id, cantidad, precio_unitario)
        )

    # Insertar en facturas con desglose de IVA
    conn.execute(
        'INSERT INTO facturas (id_venta, subtotal, porcentaje_iva, impuesto, total_usd) VALUES (?, ?, ?, ?, ?)',
        (venta_id, total, iva_rate, impuesto, total_con_iva)
    )

    conn.commit()
    conn.close()

    if 'user_id' in session:
        save_cart_to_db([])
    else:
        session.pop('cart', None)
        session.modified = True

    return jsonify({'mensaje': 'Checkout completado correctamente.', 'order_id': pedido_id, 'total': total_con_iva}), 201


# ADMIN PANEL - CARRITO POR CLIENTE
@app.route('/api/admin/cart/<int:cliente_id>', methods=['GET'])
@admin_required
def admin_get_cart(cliente_id):
    conn = get_shared_db()
    carrito_id = get_or_create_cart(conn, cliente_id)
    items = conn.execute(
        'SELECT dc.id_detalle, dc.id_producto, dc.cantidad, dc.precio_unitario, p.nombre AS name '
        'FROM detalle_carrito dc '
        'LEFT JOIN productos p ON dc.id_producto = p.id_producto '
        'WHERE dc.id_carrito = ? ORDER BY dc.id_detalle ASC',
        (carrito_id,)
    ).fetchall()
    conn.close()
    cart = [{
        'id': item['id_producto'],
        'name': item['name'] or 'Producto personalizado',
        'price': float(item['precio_unitario']),
        'quantity': item['cantidad']
    } for item in items]
    return jsonify({'cart': cart})


@app.route('/api/admin/cart/<int:cliente_id>', methods=['POST'])
@admin_required
def admin_save_cart(cliente_id):
    data = request.get_json() or {}
    items = data.get('items', [])
    conn = get_shared_db()
    carrito_id = get_or_create_cart(conn, cliente_id)
    conn.execute('DELETE FROM detalle_carrito WHERE id_carrito = ?', (carrito_id,))
    for item in items:
        conn.execute(
            'INSERT INTO detalle_carrito (id_carrito, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (carrito_id, item.get('id'), item.get('quantity', 1), item.get('price', 0))
        )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Carrito actualizado correctamente.'})


@app.route('/api/admin/invoice/create', methods=['POST'])
@admin_required
def admin_create_invoice():
    data = request.get_json() or {}
    cliente_id = data.get('cliente_id')
    items = data.get('items', [])

    if not cliente_id or not items:
        return jsonify({'message': 'Cliente y artículos son requeridos.'}), 400

    conn = get_shared_db()

    for item in items:
        pid = item.get('id')
        if pid:
            qty = int(item.get('quantity', 1))
            valid, msg = validate_stock(conn, pid, qty)
            if not valid:
                conn.close()
                return jsonify({'message': msg}), 400

    total = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in items)
    iva_rate = get_iva_rate()
    impuesto = round(total * iva_rate / 100, 2)
    total_con_iva = round(total + impuesto, 2)
    cursor = conn.execute(
        'INSERT INTO ventas (id_cliente, total) VALUES (?, ?)',
        (cliente_id, total_con_iva)
    )
    venta_id = cursor.lastrowid
    for item in items:
        conn.execute(
            'INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
            (venta_id, item.get('id'), item.get('quantity', 1), item.get('price', 0))
        )
    # Insertar en facturas con desglose de IVA
    conn.execute(
        'INSERT INTO facturas (id_venta, subtotal, porcentaje_iva, impuesto, total_usd) VALUES (?, ?, ?, ?, ?)',
        (venta_id, total, iva_rate, impuesto, total_con_iva)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Factura creada correctamente.', 'invoice_id': venta_id}), 201


# ADMIN PANEL STATIC FILES Y ENDPOINTS
@app.route('/admin-panel/')
def admin_panel_index():
    if not require_panel_admin():
        return redirect(url_for('login', next='/admin'))
    return send_from_directory(ADMIN_PANEL_DIR, 'index.html')

@app.route('/admin-panel/<path:filename>')
def admin_panel_static(filename):
    if not require_panel_admin():
        return redirect(url_for('login', next='/admin'))
    return send_from_directory(ADMIN_PANEL_DIR, filename)

@app.route('/admin')
def admin_redirect():
    if not require_panel_admin():
        return redirect(url_for('login', next='/admin'))
    return redirect('/admin-panel/')

@app.route('/login/index.html')
def login_index_html():
    next_url = request.args.get('next', '')
    return redirect(url_for('login', next=next_url))

@app.route('/api/dashboard', methods=['GET'])
@admin_required
def api_dashboard():
    conn = get_shared_db()
    stats = {}
    stats['totalSales'] = conn.execute('SELECT COUNT(*) AS total FROM ventas').fetchone()['total']
    stats['totalClients'] = conn.execute('SELECT COUNT(*) AS total FROM clientes WHERE activo = 1').fetchone()['total']
    stats['totalProducts'] = conn.execute('SELECT COUNT(*) AS total FROM productos WHERE activo = 1').fetchone()['total']
    stats['totalStock'] = conn.execute('SELECT IFNULL(SUM(stock_actual), 0) AS total FROM inventario').fetchone()['total']
    stats['totalIncome'] = conn.execute('SELECT IFNULL(SUM(total), 0) AS total FROM ventas').fetchone()['total']

    top_products = conn.execute(
        'SELECT p.nombre AS producto, SUM(d.cantidad) AS cantidad, IFNULL(SUM(d.cantidad * d.precio_unitario), 0) AS total '
        'FROM detalle_ventas d JOIN productos p ON p.id_producto = d.id_producto '
        'GROUP BY p.id_producto ORDER BY cantidad DESC LIMIT 5'
    ).fetchall()

    categories = conn.execute(
        'SELECT c.nombre AS categoria, IFNULL(SUM(i.stock_actual), 0) AS stock '
        'FROM categorias c '
        'LEFT JOIN productos p ON p.id_categoria = c.id_categoria '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'GROUP BY c.id_categoria ORDER BY stock DESC LIMIT 5'
    ).fetchall()

    monthly = conn.execute(
        "SELECT strftime('%m', fecha) AS mes, IFNULL(SUM(total), 0) AS total FROM ventas GROUP BY mes ORDER BY mes ASC"
    ).fetchall()
    conn.close()

    return jsonify({
        'stats': stats,
        'topProducts': [dict(row) for row in top_products],
        'categories': [dict(row) for row in categories],
        'monthly': [dict(row) for row in monthly]
    })

@app.route('/api/inventory', methods=['GET'])
@admin_required
def api_inventory():
    conn = get_shared_db()
    inventory = conn.execute(
        'SELECT p.id_producto, p.nombre, p.precio_venta AS precio, IFNULL(i.stock_actual, 0) AS stock, c.nombre AS categoria '
        'FROM productos p '
        'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.activo = 1 ORDER BY p.nombre ASC'
    ).fetchall()
    conn.close()
    return jsonify({'inventory': [dict(row) for row in inventory]})

@app.route('/api/clients', methods=['GET'])
@admin_required
def api_clients():
    conn = get_shared_db()
    clients = conn.execute(
        'SELECT id_cliente, nombre, correo, telefono, direccion FROM clientes WHERE activo = 1 ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'clients': [dict(row) for row in clients]})

@app.route('/api/invoices', methods=['GET'])
@admin_required
def api_invoices():
    conn = get_shared_db()
    invoices = conn.execute(
        'SELECT v.id_venta AS id, c.nombre AS cliente, v.fecha, COUNT(d.id_detalle) AS items, IFNULL(v.total, 0) AS total '
        'FROM ventas v LEFT JOIN clientes c ON v.id_cliente = c.id_cliente '
        'LEFT JOIN detalle_ventas d ON d.id_venta = v.id_venta '
        'GROUP BY v.id_venta ORDER BY v.fecha DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'invoices': [dict(row) for row in invoices]})

@app.route('/api/invoice/<int:invoice_id>', methods=['GET'])
@admin_required
def api_invoice_detail(invoice_id):
    conn = get_shared_db()
    venta = conn.execute(
        'SELECT v.id_venta AS id, c.nombre AS cliente, v.fecha, IFNULL(v.total, 0) AS total '
        'FROM ventas v LEFT JOIN clientes c ON v.id_cliente = c.id_cliente '
        'WHERE v.id_venta = ? LIMIT 1',
        (invoice_id,)
    ).fetchone()
    if not venta:
        conn.close()
        return jsonify({'message': 'Factura no encontrada.'}), 404

    detalles = conn.execute(
        'SELECT p.nombre AS producto, d.cantidad AS cantidad, IFNULL(d.precio_unitario, 0) AS precio, IFNULL(d.cantidad * d.precio_unitario, 0) AS total '
        'FROM detalle_ventas d LEFT JOIN productos p ON d.id_producto = p.id_producto '
        'WHERE d.id_venta = ?',
        (invoice_id,)
    ).fetchall()

    factura_row = conn.execute(
        'SELECT subtotal, porcentaje_iva, impuesto FROM facturas WHERE id_venta = ? LIMIT 1',
        (invoice_id,)
    ).fetchone()

    conn.close()

    invoice = dict(venta)
    if factura_row:
        invoice['subtotal'] = float(factura_row['subtotal'])
        invoice['iva_pct'] = float(factura_row['porcentaje_iva'])
        invoice['iva_amount'] = float(factura_row['impuesto'])
    else:
        invoice['subtotal'] = float(venta['total'])
        invoice['iva_pct'] = 0
        invoice['iva_amount'] = 0
    invoice['detalles'] = [dict(row) for row in detalles]
    return jsonify(invoice)


@app.route('/api/report', methods=['POST'])
@admin_required
def api_report():
    data = request.get_json() or {}
    date_from = data.get('date_from', '')
    date_to = data.get('date_to', '')

    where = ''
    params = []
    if date_from and date_to:
        where = 'WHERE v.fecha >= ? AND v.fecha <= ?'
        params = [date_from, date_to + ' 23:59:59']

    conn = get_shared_db()
    invoices = conn.execute(
        f'SELECT v.id_venta AS id, c.nombre AS cliente, v.fecha, COUNT(d.id_detalle) AS items, IFNULL(v.total, 0) AS total '
        f'FROM ventas v LEFT JOIN clientes c ON v.id_cliente = c.id_cliente '
        f'LEFT JOIN detalle_ventas d ON d.id_venta = v.id_venta '
        f'{where} '
        f'GROUP BY v.id_venta ORDER BY v.fecha DESC',
        params
    ).fetchall()

    gran_total = sum(row['total'] for row in invoices)
    conn.close()
    return jsonify({
        'invoices': [dict(row) for row in invoices],
        'gran_total': gran_total,
        'count': len(invoices)
    })


@app.route('/api/sales-data', methods=['GET'])
@admin_required
def api_sales_data():
    conn = get_shared_db()
    products = conn.execute(
        'SELECT p.id_producto, p.nombre, p.precio_venta AS precio, IFNULL(i.stock_actual, 0) AS stock '
        'FROM productos p LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.activo = 1 ORDER BY p.nombre ASC LIMIT 20'
    ).fetchall()
    clients = conn.execute(
        'SELECT id_cliente, nombre FROM clientes WHERE activo = 1 ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'products': [dict(row) for row in products], 'clients': [dict(row) for row in clients]})

@app.route('/api/product', methods=['POST'])
@admin_required
def api_create_product():
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    precio = request.form.get('precio', type=float)
    stock = request.form.get('stock', 0, type=int)
    descripcion = request.form.get('descripcion', '')

    if not nombre or not categoria or precio is None:
        return jsonify({'message': 'Nombre, categoría y precio son requeridos.'}), 400

    conn = get_shared_db()
    category_row = conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', (categoria,)).fetchone()
    if category_row:
        category_id = category_row['id_categoria']
    else:
        category_cursor = conn.execute('INSERT INTO categorias (nombre) VALUES (?)', (categoria,))
        category_id = category_cursor.lastrowid

    product_cursor = conn.execute(
        'INSERT INTO productos (nombre, descripcion, costo, precio_venta, id_categoria, activo) VALUES (?, ?, ?, ?, ?, 1)',
        (nombre, descripcion, precio, precio, category_id)
    )
    product_id = product_cursor.lastrowid
    conn.execute('INSERT INTO inventario (id_producto, stock_actual) VALUES (?, ?)', (product_id, stock))

    imagen = request.files.get('imagen')
    if imagen and imagen.filename:
        if not validate_image_file(imagen):
            conn.close()
            return jsonify({'message': 'Formato de imagen no válido o muy pesada (máx 5MB, solo PNG/JPG/GIF/WebP).'}), 400
        ext = imagen.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        imagen.save(os.path.join(images_dir, filename))
        conn.execute('INSERT INTO imagenes_productos (id_producto, ruta_imagen) VALUES (?, ?)', (product_id, filename))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto creado correctamente.', 'id_producto': product_id}), 201

@app.route('/api/product/<int:product_id>', methods=['PUT'])
@admin_required
def api_update_product(product_id):
    nombre = request.form.get('nombre')
    categoria = request.form.get('categoria')
    precio = request.form.get('precio', type=float)
    stock = request.form.get('stock', type=int)
    descripcion = request.form.get('descripcion', '')

    if not nombre or not categoria or precio is None or stock is None:
        return jsonify({'message': 'Nombre, categoría, precio y stock son requeridos.'}), 400

    conn = get_shared_db()
    category_row = conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', (categoria,)).fetchone()
    if category_row:
        category_id = category_row['id_categoria']
    else:
        category_cursor = conn.execute('INSERT INTO categorias (nombre) VALUES (?)', (categoria,))
        category_id = category_cursor.lastrowid

    conn.execute('UPDATE productos SET nombre = ?, descripcion = ?, precio_venta = ?, id_categoria = ? WHERE id_producto = ?',
                 (nombre, descripcion, precio, category_id, product_id))
    existing_inv = conn.execute('SELECT id_inventario FROM inventario WHERE id_producto = ?', (product_id,)).fetchone()
    if existing_inv:
        conn.execute('UPDATE inventario SET stock_actual = ? WHERE id_producto = ?', (stock, product_id))
    else:
        conn.execute('INSERT INTO inventario (id_producto, stock_actual) VALUES (?, ?)', (product_id, stock))

    imagen = request.files.get('imagen')
    if imagen and imagen.filename:
        if not validate_image_file(imagen):
            conn.close()
            return jsonify({'message': 'Formato de imagen no válido o muy pesada (máx 5MB, solo PNG/JPG/GIF/WebP).'}), 400
        ext = imagen.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filename = f"{uuid.uuid4().hex}.{ext}"
        images_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'images')
        os.makedirs(images_dir, exist_ok=True)
        imagen.save(os.path.join(images_dir, filename))
        existing_img = conn.execute('SELECT id_imagen FROM imagenes_productos WHERE id_producto = ? LIMIT 1', (product_id,)).fetchone()
        if existing_img:
            conn.execute('UPDATE imagenes_productos SET ruta_imagen = ? WHERE id_producto = ?', (filename, product_id))
        else:
            conn.execute('INSERT INTO imagenes_productos (id_producto, ruta_imagen) VALUES (?, ?)', (product_id, filename))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto actualizado correctamente.'})

@app.route('/api/product/<int:product_id>', methods=['DELETE'])
@admin_required
def api_delete_product(product_id):
    conn = get_shared_db()
    conn.execute('DELETE FROM imagenes_productos WHERE id_producto = ?', (product_id,))
    conn.execute('DELETE FROM inventario WHERE id_producto = ?', (product_id,))
    conn.execute('DELETE FROM productos WHERE id_producto = ?', (product_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto eliminado correctamente.'})

@app.route('/api/client', methods=['POST'])
@admin_required
def api_create_client():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    telefono = data.get('telefono', '')
    direccion = data.get('direccion', '')

    if not nombre or not correo:
        return jsonify({'message': 'Nombre y correo son requeridos.'}), 400

    conn = get_shared_db()
    conn.execute('INSERT INTO clientes (nombre, correo, telefono, direccion, activo) VALUES (?, ?, ?, ?, 1)',
                 (nombre, correo, telefono, direccion))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente creado correctamente.'}), 201

@app.route('/api/client/<int:client_id>', methods=['PUT'])
@admin_required
def api_update_client(client_id):
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    telefono = data.get('telefono', '')
    direccion = data.get('direccion', '')

    if not nombre or not correo:
        return jsonify({'message': 'Nombre y correo son requeridos.'}), 400

    conn = get_shared_db()
    conn.execute('UPDATE clientes SET nombre = ?, correo = ?, telefono = ?, direccion = ? WHERE id_cliente = ? AND activo = 1',
                 (nombre, correo, telefono, direccion, client_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente actualizado correctamente.'})

@app.route('/api/client/<int:client_id>', methods=['DELETE'])
@admin_required
def api_delete_client(client_id):
    conn = get_shared_db()
    conn.execute('UPDATE clientes SET activo = 0 WHERE id_cliente = ?', (client_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente eliminado correctamente.'})

# Migración: agregar columnas si no existen
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE usuarios ADD COLUMN telefono VARCHAR(20)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE clientes ADD COLUMN cedula VARCHAR(20)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE envios ADD COLUMN metodo_pago VARCHAR(50)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE envios ADD COLUMN referencia_pago VARCHAR(100)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE envios ADD COLUMN tipo_envio VARCHAR(50)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE configuracion ADD COLUMN tasa_eur DECIMAL(12,4)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('ALTER TABLE configuracion ADD COLUMN tasa_usd DECIMAL(12,4)')
    conn.commit()
except Exception:
    pass
try:
    conn = get_shared_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS password_resets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_usuario INTEGER NOT NULL,
        token VARCHAR(64) NOT NULL UNIQUE,
        expires_at DATETIME NOT NULL,
        used INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario)
    )''')
    conn.commit()
except Exception:
    pass
conn.close()

# Semillas en la base de datos compartida (esquema SQL en español)
conn = get_shared_db()
try:
    total = conn.execute('SELECT COUNT(*) AS total FROM productos').fetchone()['total']
except Exception:
    total = 0

# Migrar categorías: insertar las 7 estándar + Personalizado
all_categories = CATEGORIES + ['Personalizado']
for cat_name in all_categories:
    existing = conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', (cat_name,)).fetchone()
    if not existing:
        conn.execute('INSERT INTO categorias (nombre) VALUES (?)', (cat_name,))

# Reasignar productos con categorías antiguas a 'camisas' y eliminar las viejas
old_cats = [dict(r) for r in conn.execute(
    'SELECT id_categoria, nombre FROM categorias WHERE nombre NOT IN ({})'.format(
        ','.join('?' for _ in all_categories)
    ), all_categories
).fetchall()]
if old_cats:
    default_cat = dict(conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', ('camisas',)).fetchone())
    default_id = default_cat['id_categoria']
    for old in old_cats:
        conn.execute('UPDATE productos SET id_categoria = ? WHERE id_categoria = ?', (default_id, old['id_categoria']))
        conn.execute('DELETE FROM categorias WHERE id_categoria = ?', (old['id_categoria'],))

if total == 0:
    taza_cat = conn.execute('SELECT id_categoria FROM categorias WHERE nombre = ? LIMIT 1', ('tazas',)).fetchone()
    cat_id = taza_cat['id_categoria']

    sample_products = [
        ('Taza Baki', 'Taza Baki personalizada', 15.00, 'taza baki.jpeg'),
        ('Taza con Flores', 'Taza con flores', 12.00, 'taza con flores.jpeg'),
        ('Taza Hollow Knight', 'Taza Hollow Knight', 15.00, 'taza hollow knight.jpeg'),
        ('Taza Mensaje Motivador', 'Taza con mensaje motivador', 10.00, 'taza mensaje 1.jpeg'),
        ('Taza Poo Emoji', 'Taza Poo Emoji', 12.00, 'taza poo.jpeg'),
        ('Taza Sabra Pepe', 'Taza Sabra Pepe', 15.00, 'taza sabra pepe.jpeg'),
        ('Taza Spiderman', 'Taza Spiderman', 15.00, 'taza spiderman.jpeg'),
        ('Taza Trofeo #1 Mamá', 'Taza Trofeo Mamá', 18.00, 'taza trofeo #1 mama.jpeg')
    ]

    for nombre, descripcion, precio, imagen in sample_products:
        cur = conn.execute(
            'INSERT INTO productos (nombre, descripcion, costo, precio_venta, id_categoria, activo) VALUES (?, ?, ?, ?, ?, 1)',
            (nombre, descripcion, precio, precio, cat_id)
        )
        prod_id = cur.lastrowid
        conn.execute('INSERT INTO imagenes_productos (id_producto, ruta_imagen) VALUES (?, ?)', (prod_id, imagen))

    conn.commit()

conn.close()

# =========================================================
# Password recovery via email
# =========================================================
import smtplib
import secrets
from email.mime.text import MIMEText
from datetime import datetime, timedelta

SMTP_HOST = os.environ.get('SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
MAIL_FROM = os.environ.get('MAIL_FROM', 'noreply@sublime.com')

def send_reset_email(to_email, token):
    if not SMTP_HOST or not SMTP_USER:
        return False
    reset_url = url_for('reset_password', token=token, _external=True)
    msg = MIMEText(f'''Hola,

Recibimos una solicitud para restablecer tu contraseña en Sublime's.

Haz clic en el siguiente enlace para crear una nueva contraseña:

{reset_url}

Este enlace expira en 1 hora.

Si no solicitaste este cambio, ignora este mensaje.

— Sublime's''')
    msg['Subject'] = 'Restablecimiento de contraseña - Sublime\'s'
    msg['From'] = MAIL_FROM
    msg['To'] = to_email
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        return False

@app.route('/api/forgot', methods=['POST'])
def api_forgot():
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    conn = get_shared_db()
    user = conn.execute('SELECT id_usuario, nombre, correo FROM usuarios WHERE correo = ? LIMIT 1', (email,)).fetchone()
    conn.close()

    # Always return success to avoid user enumeration
    if not user:
        return jsonify({'mensaje': 'Si el correo está registrado, recibirás un enlace de recuperación.'})

    token = secrets.token_urlsafe(48)
    expires_at = (datetime.utcnow() + timedelta(hours=1)).isoformat()

    conn = get_shared_db()
    conn.execute('INSERT INTO password_resets (id_usuario, token, expires_at) VALUES (?, ?, ?)',
                 (user['id_usuario'], token, expires_at))
    conn.commit()
    conn.close()

    sent = send_reset_email(user['correo'], token)
    if not sent:
        # If email is not configured, show the link directly in the response (dev mode)
        reset_url = url_for('reset_password', token=token, _external=True)
        app.logger.warning(f'SMTP not configured. Reset link: {reset_url}')
        return jsonify({'mensaje': 'Correo no configurado. Usa el enlace de depuración.', 'debug_url': reset_url})

    return jsonify({'mensaje': 'Si el correo está registrado, recibirás un enlace de recuperación.'})

@app.route('/recuperar/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_shared_db()
    row = conn.execute(
        'SELECT id_usuario, expires_at, used FROM password_resets WHERE token = ? LIMIT 1',
        (token,)
    ).fetchone()

    if not row:
        conn.close()
        flash('Enlace de recuperación inválido.', 'error')
        return redirect(url_for('login'))

    if row['used']:
        conn.close()
        flash('Este enlace ya fue utilizado.', 'error')
        return redirect(url_for('login'))

    try:
        expires = datetime.fromisoformat(row['expires_at'])
        if datetime.utcnow() > expires:
            conn.close()
            flash('El enlace ha expirado. Solicita uno nuevo.', 'error')
            return redirect(url_for('login'))
    except Exception:
        pass

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        elif password != confirm:
            flash('Las contraseñas no coinciden.', 'error')
        else:
            conn.execute('UPDATE usuarios SET contraseña = ? WHERE id_usuario = ?',
                         (generate_password_hash(password), row['id_usuario']))
            conn.execute('UPDATE password_resets SET used = 1 WHERE token = ?', (token,))
            conn.commit()
            conn.close()
            flash('Contraseña actualizada con éxito. Ya puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))

    conn.close()
    return render_template('reset_password.html', token=token)


@app.route('/')
def home():
    trending = fetch_products(sort_option='newest', limit=8)
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('index.html', trending=trending, cart_count=cart_count)

@app.route('/catalogo')
def catalogo():
    categoria = request.args.get('categoria')
    search_query = request.args.get('q')
    sort_option = request.args.get('sort')
    productos = fetch_products(categoria=categoria, search_query=search_query, sort_option=sort_option)
    
    # Obtener categorías para el filtro
    conn = get_shared_db()
    db_cats = {row['nombre'] for row in conn.execute('SELECT nombre FROM categorias').fetchall()}
    conn.close()
    order = CATEGORIES + ['Personalizado']
    categorias_list = [c for c in order if c in db_cats]
    
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('catalogo.html', productos=productos, categorias=categorias_list, cart_count=cart_count)

@app.route('/producto/<int:id>')
def producto(id):
    p = fetch_product_by_id(id)
    if not p:
        if '404.html' in os.listdir(os.path.join(BASE_DIR, 'templates')):
            return render_template('404.html'), 404
        return 'Producto no encontrado', 404
    return render_template('producto.html', producto=p)

@app.route('/personalizar', methods=['GET', 'POST'])
def personalizar():
    if request.method == 'POST':
        # Capturar todos los detalles de personalización
        product_type = request.form.get('product_type')
        size = request.form.get('size')
        color = request.form.get('product_color')
        material = request.form.get('material')
        text = request.form.get('custom_text')
        font = request.form.get('font_style')
        placement = request.form.get('placement')
        
        custom_details = f"({product_type.capitalize()}, {size}, {color}, {material})"
        if text:
            custom_details += f" con texto: '{text}' ({font}) en {placement}"
            
        # Crear producto personalizado en DB con nombre identificable
        conn = get_shared_db()
        product_id = get_or_create_custom_product(conn, name=f"Personalizado - {product_type.capitalize()}", description=custom_details, price=30.0)
        conn.close()
        
        flash('Diseño personalizado añadido al carrito.', 'success')
        cart = load_cart_from_db() if 'user_id' in session else session.get('cart', [])
        if not isinstance(cart, list):
            cart = []
        
        cart.append({
            'id': product_id,
            'name': f'Personalizado: {product_type.capitalize()}', 
            'details': custom_details,
            'price': 30.00,
            'quantity': 1
        })
        
        if 'user_id' in session:
            save_cart_to_db(cart)
        else:
            session['cart'] = cart
            session.modified = True
        
        return redirect(url_for('carrito'))
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('personalizar.html', cart_count=cart_count)

@app.route('/agregar_carrito/<int:id>')
def agregar_carrito(id):
    p = fetch_product_by_id(id)
    if not p:
        flash('Producto no encontrado.', 'error')
        return redirect(url_for('catalogo'))

    cart = load_cart_from_db() if 'user_id' in session else session.get('cart', [])
    if not isinstance(cart, list):
        cart = []
    
    # Verificar si ya está en carrito
    existing = next((item for item in cart if item.get('id') == id), None)
    if existing:
        existing['quantity'] += 1
    else:
        cart.append({'id': p['id'], 'name': p['name'], 'price': p['price'], 'quantity': 1})
    
    if 'user_id' in session:
        save_cart_to_db(cart)
    else:
        session['cart'] = cart
        session.modified = True
    
    flash(f"{p['name']} añadido al carrito.", 'success')
    return redirect(url_for('catalogo'))

@app.route('/carrito')
def carrito():
    if 'user_id' in session:
        cart = load_cart_from_db()
    else:
        cart = session.get('cart', [])
    
    # Enrich session cart items with image_url
    for item in cart:
        if 'image_url' not in item or not item.get('image_url'):
            if item.get('id'):
                conn = get_shared_db()
                row = conn.execute(
                    'SELECT ruta_imagen FROM imagenes_productos WHERE id_producto = ? LIMIT 1',
                    (item['id'],)
                ).fetchone()
                conn.close()
                item['image_url'] = row['ruta_imagen'] if row else 'placeholder.png'
            else:
                item['image_url'] = 'placeholder.png'
    
    total = sum(item['price'] * item.get('quantity', 1) for item in cart)
    return render_template('carrito.html', cart=cart, total=total, cart_count=len(cart))

@app.route('/eliminar_carrito/<int:index>')
def eliminar_carrito(index):
    if 'user_id' in session:
        cart = load_cart_from_db()
        if isinstance(cart, list) and 0 <= index < len(cart):
            cart.pop(index)
            save_cart_to_db(cart)
    else:
        cart = session.get('cart', [])
        if isinstance(cart, list) and 0 <= index < len(cart):
            cart.pop(index)
            session['cart'] = cart
            session.modified = True

    return redirect(url_for('carrito'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'user_id' in session:
        full_cart = load_cart_from_db()
    else:
        full_cart = session.get('cart', [])
    
    if not full_cart:
        flash('Tu carrito está vacío.', 'error')
        return redirect(url_for('catalogo'))

    # Handle selected indices from cart page (POST with selected_indices)
    selected_indices = request.form.get('selected_indices')
    if selected_indices:
        try:
            indices = json.loads(selected_indices)
            if isinstance(indices, list) and len(indices) > 0:
                session['checkout_items'] = [full_cart[i] for i in indices if i < len(full_cart)]
                session.modified = True
            else:
                session['checkout_items'] = list(full_cart)
        except (json.JSONDecodeError, TypeError, IndexError):
            session['checkout_items'] = list(full_cart)
        return redirect(url_for('checkout'))

    # Use stored checkout items if available
    if 'checkout_items' in session:
        cart = session['checkout_items']
    else:
        cart = full_cart

    total = sum(item['price'] * item.get('quantity', 1) for item in cart)

    if request.method == 'POST' and request.form.get('name'):
        name = request.form.get('name', 'Cliente')
        telefono = request.form.get('telefono', '').strip()
        cedula = request.form.get('cedula', '').strip()
        shipping_method = request.form.get('shipping_method', 'destino')
        empresa_envio = request.form.get('empresa_envio', '')
        codigo_agencia = request.form.get('codigo_agencia', '').strip()
        ciudad = request.form.get('ciudad', '').strip()
        estado = request.form.get('estado', '').strip()
        payment_method = request.form.get('payment_method')
        reference = request.form.get('reference', '')

        # Compose address from new fields
        if shipping_method == 'tienda':
            address = 'Retiro en Tienda — Av. Principal, Local 5, CC La Cascada, Caracas'
        else:
            parts = []
            if empresa_envio: parts.append(empresa_envio)
            if codigo_agencia: parts.append('Cód: ' + codigo_agencia)
            if ciudad: parts.append(ciudad)
            if estado: parts.append(estado)
            address = ', '.join(parts) if parts else 'Por especificar'

        # Build a descriptive empresa_envio that includes shipping type
        tipo_labels = {'destino': 'Cobro a Destino', 'tienda': 'Retiro en Tienda', 'agencia': 'Retirar en Agencia'}
        tipo_label = tipo_labels.get(shipping_method, '')
        if shipping_method in ('destino', 'agencia') and empresa_envio:
            envio_desc = f'{tipo_label} - {empresa_envio}'
        else:
            envio_desc = tipo_label

        conn = get_shared_db()
        ensure_order_statuses(conn)

        # Validar stock antes de continuar
        for item in cart:
            product_id = item.get('id')
            if product_id:
                valid, msg = validate_stock(conn, product_id, item.get('quantity', 1))
                if not valid:
                    conn.close()
                    flash(msg, 'error')
                    return redirect(url_for('carrito'))

        cliente_id = get_or_create_client(conn, session.get('user_email'), name, address, telefono, cedula)
        status = conn.execute('SELECT id_estado FROM estados_pedido WHERE nombre = ? LIMIT 1', ('Pendiente',)).fetchone()
        status_id = status['id_estado'] if status else 1

        iva_rate = get_iva_rate()
        impuesto = round(total * iva_rate / 100, 2)
        total_con_iva = round(total + impuesto, 2)
        pedido_cursor = conn.execute(
            'INSERT INTO pedidos (id_cliente, id_estado, total) VALUES (?, ?, ?)',
            (cliente_id, status_id, total_con_iva)
        )
        pedido_id = pedido_cursor.lastrowid

        for item in cart:
            product_id = item.get('id')
            if not product_id:
                product_id = get_or_create_custom_product(conn)
            cantidad = item.get('quantity', 1)
            conn.execute(
                'INSERT INTO detalle_pedidos (id_pedido, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
                (pedido_id, product_id, cantidad, item['price'])
            )

        conn.execute(
            'INSERT INTO envios (id_pedido, direccion_envio, empresa_envio, numero_guia, estado_envio, fecha_envio, metodo_pago, referencia_pago, tipo_envio) VALUES (?, ?, ?, ?, ?, datetime("now"), ?, ?, ?)',
            (pedido_id, address, envio_desc, '', 'Pendiente', payment_method, reference, shipping_method)
        )

        # También crear registro en ventas / detalle_ventas para que aparezca en Facturas del admin
        venta_cursor = conn.execute(
            'INSERT INTO ventas (id_cliente, total) VALUES (?, ?)',
            (cliente_id, total_con_iva)
        )
        venta_id = venta_cursor.lastrowid
        for item in cart:
            product_id = item.get('id')
            if not product_id:
                product_id = get_or_create_custom_product(conn)
            conn.execute(
                'INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario) VALUES (?, ?, ?, ?)',
                (venta_id, product_id, item.get('quantity', 1), item['price'])
            )

        # Insertar en facturas con desglose de IVA
        conn.execute(
            'INSERT INTO facturas (id_venta, subtotal, porcentaje_iva, impuesto, total_usd) VALUES (?, ?, ?, ?, ?)',
            (venta_id, total, iva_rate, impuesto, total_con_iva)
        )

        conn.commit()
        conn.close()

        # Limpiar carrito y checkout
        if 'checkout_items' in session:
            session.pop('checkout_items', None)
        if 'user_id' in session:
            save_cart_to_db([])
        else:
            session.pop('cart', None)
        
        return redirect(url_for('factura', order_id=pedido_id))

    cart_count = len(cart)
    return render_template('checkout.html', total=total, cart_count=cart_count, item_count=len(cart))

@app.route('/factura/<int:order_id>')
def factura(order_id):
    conn = get_shared_db()
    order_row = conn.execute(
        'SELECT p.id_pedido AS id, p.total, p.fecha, e.nombre AS estado, c.nombre AS cliente, c.correo, '
        'env.direccion_envio AS address, env.empresa_envio AS empresa_envio, '
        'env.metodo_pago AS payment_method, env.referencia_pago AS reference, env.tipo_envio AS tipo_envio '
        'FROM pedidos p '
        'LEFT JOIN estados_pedido e ON p.id_estado = e.id_estado '
        'LEFT JOIN clientes c ON p.id_cliente = c.id_cliente '
        'LEFT JOIN envios env ON env.id_pedido = p.id_pedido '
        'WHERE p.id_pedido = ? LIMIT 1',
        (order_id,)
    ).fetchone()

    if not order_row:
        conn.close()
        if '404.html' in os.listdir(os.path.join(BASE_DIR, 'templates')):
            return render_template('404.html'), 404
        return 'Pedido no encontrado', 404

    items = conn.execute(
        'SELECT dp.cantidad, dp.precio_unitario, pr.nombre AS name '
        'FROM detalle_pedidos dp '
        'LEFT JOIN productos pr ON dp.id_producto = pr.id_producto '
        'WHERE dp.id_pedido = ?',
        (order_id,)
    ).fetchall()
    conn.close()

    items_subtotal = sum(float(item['precio_unitario']) * int(item['cantidad']) for item in items)
    iva_rate = get_iva_rate()
    iva_amount = round(items_subtotal * iva_rate / 100, 2)
    total_final = round(items_subtotal + iva_amount, 2)

    items_list = [
        {
            'name': item['name'] or 'Producto personalizado',
            'price': item['precio_unitario'] * item['cantidad'],
            'details': f'Cantidad: {item["cantidad"]}' if item['cantidad'] and item['cantidad'] > 1 else ''
        }
        for item in items
    ]

    order = {
        'id': order_row['id'],
        'subtotal': items_subtotal,
        'iva_pct': iva_rate,
        'iva_amount': iva_amount,
        'total': total_final,
        'address': order_row['address'] or '',
        'payment_method': order_row['payment_method'] or '',
        'reference': order_row['reference'] or '',
        'empresa_envio': order_row['empresa_envio'] or '',
        'tipo_envio': order_row['tipo_envio'] or '',
    }
    return render_template('factura.html', order=order, items=items_list)

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    cart_count = get_cart_count()

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_shared_db()
        user = conn.execute(
            'SELECT u.id_usuario, u.nombre, u.correo, u.contraseña AS password, r.nombre AS rol '
            'FROM usuarios u LEFT JOIN roles r ON u.id_rol = r.id_rol '
            'WHERE u.correo = ? OR u.nombre = ? LIMIT 1',
            (username, username)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id_usuario']
            session['username'] = user['nombre']
            session['user_email'] = user['correo']
            session['user_role'] = user.get('rol') or 'Trabajador'

            guest_cart = session.get('cart', [])
            merge_guest_cart_into_db(guest_cart)

            if user['correo'].lower() == 'admin@sublime.com':
                flash(f'¡Bienvenido al panel administrativo, {user["nombre"]}!', 'success')
                return redirect(url_for('admin_panel_index'))

            next_url = request.form.get('next') or request.args.get('next') or url_for('home')
            if not is_safe_url(next_url):
                next_url = url_for('home')
            flash(f'¡Bienvenido de nuevo, {user["nombre"]}!', 'success')
            return redirect(next_url)
        else:
            flash('Credenciales inválidas.', 'error')

    return render_template('login.html', cart_count=cart_count)


@app.route('/registro', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def registro():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        telefono = request.form.get('telefono', '')

        conn = get_shared_db()
        existing_user = conn.execute(
            'SELECT id_usuario FROM usuarios WHERE nombre = ? OR correo = ? LIMIT 1',
            (username, email)
        ).fetchone()

        if existing_user:
            flash('El nombre de usuario o email ya está en uso.', 'error')
        else:
            # Asignar rol Trabajador (2) si existe, o Administrador por defecto
            role = conn.execute('SELECT id_rol FROM roles WHERE nombre = ? LIMIT 1', ('Trabajador',)).fetchone()
            role_id = role['id_rol'] if role else 2
            conn.execute(
                'INSERT INTO usuarios (id_usuario, nombre, correo, contraseña, id_rol, telefono) VALUES (NULL, ?, ?, ?, ?, ?)',
                (username, email, generate_password_hash(password), role_id, telefono)
            )
            conn.commit()
            flash('Cuenta creada exitosamente. ¡Bienvenido!', 'success')
            conn.close()
            return redirect(url_for('login'))

        conn.close()

    return render_template('registro.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_email', None)
    flash('Has cerrado sesión.', 'success')
    return redirect(url_for('home'))


@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        asunto = request.form.get('asunto')
        mensaje = request.form.get('mensaje')
        # Aquí podríamos guardar el mensaje en la DB o enviarlo por correo.
        flash('Mensaje enviado. Gracias por contactarnos.', 'success')
        return redirect(url_for('contacto'))
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('contacto.html', cart_count=cart_count)


@app.route('/ayuda')
def ayuda():
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('ayuda.html', cart_count=cart_count)


@app.route('/terminos')
def terminos():
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('terminos.html', cart_count=cart_count)


@app.route('/privacidad')
def privacidad():
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('privacidad.html', cart_count=cart_count)


@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = load_current_user()
    if not user:
        flash('No se encontró información de usuario. Inicia sesión nuevamente.', 'error')
        return redirect(url_for('logout'))

    if request.method == 'POST':
        action = request.form.get('action')
        conn = get_shared_db()

        if action == 'cambiar_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            row = conn.execute('SELECT contraseña FROM usuarios WHERE id_usuario = ? LIMIT 1', (session['user_id'],)).fetchone()
            if not row or not check_password_hash(row['contraseña'], current_pw):
                flash('La contraseña actual no es correcta.', 'error')
            elif len(new_pw) < 6:
                flash('La nueva contraseña debe tener al menos 6 caracteres.', 'error')
            elif new_pw != confirm_pw:
                flash('Las contraseñas nuevas no coinciden.', 'error')
            else:
                conn.execute('UPDATE usuarios SET contraseña = ? WHERE id_usuario = ?', (generate_password_hash(new_pw), session['user_id']))
                conn.commit()
                flash('Contraseña actualizada con éxito.', 'success')

        elif action == 'cambiar_email':
            new_email = request.form.get('new_email', '').strip()
            if not new_email or '@' not in new_email:
                flash('Ingresa un correo electrónico válido.', 'error')
            else:
                existing = conn.execute('SELECT id_usuario FROM usuarios WHERE correo = ? AND id_usuario != ? LIMIT 1', (new_email, session['user_id'])).fetchone()
                if existing:
                    flash('Ese correo ya está en uso por otro usuario.', 'error')
                else:
                    conn.execute('UPDATE usuarios SET correo = ? WHERE id_usuario = ?', (new_email, session['user_id']))
                    conn.commit()
                    session['user_email'] = new_email
                    flash('Correo electrónico actualizado con éxito.', 'success')

        elif action == 'cambiar_telefono':
            phone = request.form.get('phone', '').strip()
            conn.execute('UPDATE usuarios SET telefono = ? WHERE id_usuario = ?', (phone, session['user_id']))
            conn.commit()
            flash('Teléfono actualizado con éxito.', 'success')

        conn.close()
        return redirect(url_for('perfil'))

    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    conn = get_shared_db()
    links = conn.execute('SELECT proveedor, proveedor_correo FROM cuentas_vinculadas WHERE id_usuario = ?', (session['user_id'],)).fetchall()
    conn.close()
    linked_accounts = {row['proveedor']: row['proveedor_correo'] for row in links}
    return render_template('perfil.html', user=user, cart_count=cart_count, linked_accounts=linked_accounts)


@app.route('/auth/google/callback')
def auth_google_callback():
    code = request.args.get('code')
    state = request.args.get('state', '')
    error = request.args.get('error')
    if error or not code:
        flash(f'Error al iniciar sesión con Google: {error or "Código no recibido"}', 'error')
        return render_template('popup_close.html')
    link_mode = state == 'link'
    try:
        user_info = exchange_google_code(code)
    except Exception as e:
        flash(f'Error al conectar con Google: {str(e)}', 'error')
        return render_template('popup_close.html')
    provider_id = f"google_{user_info['id']}"
    email = user_info.get('email', '')
    username = user_info.get('name', user_info.get('given_name', 'Google User'))
    conn = get_shared_db()
    if link_mode and 'user_id' in session:
        current_user_id = session['user_id']
        existing = conn.execute('SELECT id_usuario FROM cuentas_vinculadas WHERE proveedor = "google" AND proveedor_id = ? LIMIT 1', (provider_id,)).fetchone()
        if existing:
            flash('Esta cuenta de Google ya está vinculada a otro usuario.' if existing['id_usuario'] != current_user_id else 'Esta cuenta de Google ya está vinculada a tu cuenta.', 'info')
        else:
            try:
                conn.execute('INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, "google", ?, ?)', (current_user_id, provider_id, email))
                conn.commit()
                flash('Cuenta de Google vinculada exitosamente.', 'success')
            except sqlite3.IntegrityError:
                flash('Ya tienes una cuenta de Google vinculada a este perfil.', 'error')
        conn.close()
        return render_template('popup_close.html')
    linked = conn.execute('SELECT id_usuario FROM cuentas_vinculadas WHERE proveedor = "google" AND proveedor_id = ? LIMIT 1', (provider_id,)).fetchone()
    if linked:
        user_id = linked['id_usuario']
        user_row = conn.execute('SELECT nombre, correo FROM usuarios WHERE id_usuario = ? LIMIT 1', (user_id,)).fetchone()
        if user_row:
            username = user_row['nombre']
            email = user_row['correo']
        else:
            conn.execute('DELETE FROM cuentas_vinculadas WHERE proveedor = "google" AND proveedor_id = ?', (provider_id,))
            conn.commit()
            linked = None
    if not linked:
        user = conn.execute('SELECT id_usuario, nombre FROM usuarios WHERE correo = ? LIMIT 1', (email,)).fetchone()
        if user:
            user_id = user['id_usuario']
            username = user['nombre']
            try:
                conn.execute('INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, "google", ?, ?)', (user_id, provider_id, email))
                conn.commit()
            except sqlite3.IntegrityError:
                pass
        else:
            role = conn.execute('SELECT id_rol FROM roles WHERE nombre = ? LIMIT 1', ('Trabajador',)).fetchone()
            role_id = role['id_rol'] if role else 2
            cursor = conn.execute('INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)', (username, email, generate_password_hash('oauth_' + uuid.uuid4().hex[:8]), role_id))
            user_id = cursor.lastrowid
            conn.execute('INSERT INTO cuentas_vinculadas (id_usuario, proveedor, proveedor_id, proveedor_correo) VALUES (?, "google", ?, ?)', (user_id, provider_id, email))
            conn.commit()
    conn.close()
    session['user_id'] = user_id
    session['username'] = username
    session['user_email'] = email
    guest_cart = session.get('cart', [])
    merge_guest_cart_into_db(guest_cart)
    flash('¡Bienvenido! Iniciaste sesión exitosamente con Google.', 'success')
    return render_template('popup_close.html')


@app.route('/login/google')
def login_google():
    if not GOOGLE_CLIENT_ID:
        flash('Google Login no está configurado. Configura GOOGLE_CLIENT_ID.', 'error')
        return redirect(url_for('login'))
    state = 'link' if 'user_id' in session else ''
    return redirect(google_oauth_url(state=state))


@app.route('/auth/facebook/callback')
def auth_facebook_callback():
    flash('Facebook Login no está disponible actualmente.', 'error')
    return render_template('popup_close.html')


@app.route('/login/facebook')
def login_facebook():
    flash('Facebook Login no está disponible actualmente. Usa Google o crea una cuenta.', 'error')
    return redirect(url_for('login'))


@app.route('/perfil/desvincular/<proveedor>', methods=['POST'])
def unlink_social(proveedor):
    if 'user_id' not in session:
        flash('Debes iniciar sesión para desvincular una cuenta.', 'error')
        return redirect(url_for('login'))

    if proveedor not in ['google', 'facebook']:
        flash('Proveedor inválido.', 'error')
        return redirect(url_for('perfil'))

    conn = get_shared_db()
    try:
        user = conn.execute('SELECT contraseña FROM usuarios WHERE id_usuario = ? LIMIT 1', (session['user_id'],)).fetchone()
        other_links = conn.execute('SELECT COUNT(*) AS total FROM cuentas_vinculadas WHERE id_usuario = ? AND proveedor != ?', (session['user_id'], proveedor)).fetchone()

        has_password = user and user['contraseña'] != 'oauth_simulated' and len(user['contraseña']) > 0
        has_other_link = other_links and other_links['total'] > 0

        if not has_password and not has_other_link:
            flash('No puedes desvincular esta cuenta. Debes establecer una contraseña o vincular otro método de inicio de sesión primero.', 'error')
        else:
            conn.execute('DELETE FROM cuentas_vinculadas WHERE id_usuario = ? AND proveedor = ?', (session['user_id'], proveedor))
            conn.commit()
            flash(f'Cuenta de {proveedor.capitalize()} desvinculada exitosamente.', 'success')
    except Exception:
        flash('Ocurrió un error al desvincular la cuenta.', 'error')
    finally:
        conn.close()

    return redirect(url_for('perfil'))


@app.route('/mis-pedidos')
def mis_pedidos():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    cart_count = len(load_cart_from_db()) if 'user_id' in session else len(session.get('cart', []))
    return render_template('mis_pedidos.html', cart_count=cart_count)


if __name__ == '__main__':
    app.run(debug=False, port=5000)
