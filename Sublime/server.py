from flask import Flask, request, jsonify, redirect
import sqlite3
import os

try:
    import mysql.connector
except ImportError:
    mysql = None

app = Flask(__name__, static_folder='.', static_url_path='')

# Configuración de base de datos
BD_DIR = os.path.join(os.path.dirname(__file__), 'BD')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_SQL_FILE = os.path.join(BD_DIR, 'database.sql')
SQLITE_DB_FILE = os.path.join(BD_DIR, 'database.db')
SQLITE_FALLBACK = os.path.join(DATA_DIR, 'sublime.db')

MYSQL_CONFIG = {
    'host': os.getenv('MYSQL_HOST', ''),
    'port': int(os.getenv('MYSQL_PORT', 3306)),
    'user': os.getenv('MYSQL_USER', ''),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('MYSQL_DATABASE', 'sublime_db'),
}
USE_MYSQL = bool(MYSQL_CONFIG['host'] and MYSQL_CONFIG['user'] and MYSQL_CONFIG['password'])

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)


def create_sqlite_db(path):
    if not os.path.exists(DB_SQL_FILE):
        raise RuntimeError('No se encontró BD/database.sql para crear la base SQLite.')
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys = ON')
    with open(DB_SQL_FILE, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def create_mysql_db():
    if mysql is None:
        raise RuntimeError('mysql-connector-python no está instalado.')
    conn = mysql.connector.connect(
        host=MYSQL_CONFIG['host'],
        port=MYSQL_CONFIG['port'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{MYSQL_CONFIG['database']}` DEFAULT CHARACTER SET utf8mb4")
    cursor.close()
    conn.close()

    conn = mysql.connector.connect(**MYSQL_CONFIG)
    cursor = conn.cursor()
    if not os.path.exists(DB_SQL_FILE):
        raise RuntimeError('No se encontró BD/database.sql para crear la base MySQL.')
    with open(DB_SQL_FILE, 'r', encoding='utf-8') as f:
        for _ in cursor.execute(f.read(), multi=True):
            pass
    conn.commit()
    cursor.close()
    conn.close()


def get_db():
    if USE_MYSQL:
        if mysql is None:
            raise RuntimeError('mysql-connector-python no está instalado.')
        return mysql.connector.connect(**MYSQL_CONFIG)

    db_path = SQLITE_DB_FILE if os.path.exists(SQLITE_DB_FILE) else SQLITE_FALLBACK
    if not os.path.exists(db_path):
        create_sqlite_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if USE_MYSQL:
        create_mysql_db()
        conn = get_db()
        cursor = conn.cursor()
    else:
        if not os.path.exists(SQLITE_DB_FILE) and not os.path.exists(SQLITE_FALLBACK):
            create_sqlite_db(SQLITE_DB_FILE)
        conn = get_db()
        conn.execute('PRAGMA foreign_keys = ON')
        cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM roles')
    role_count = cursor.fetchone()[0]
    if role_count == 0:
        if USE_MYSQL:
            cursor.execute('INSERT INTO roles (nombre) VALUES (%s), (%s)', ('Administrador', 'Trabajador'))
        else:
            cursor.execute('INSERT INTO roles (nombre) VALUES (?), (?)', ('Administrador', 'Trabajador'))

    cursor.execute('SELECT COUNT(*) FROM usuarios')
    user_count = cursor.fetchone()[0]
    if user_count == 0:
        if USE_MYSQL:
            cursor.execute(
                'INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (%s, %s, %s, %s)',
                ('Administrador', 'admin@sublime.com', 'admin123', 1)
            )
        else:
            cursor.execute(
                'INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)',
                ('Administrador', 'admin@sublime.com', 'admin123', 1)
            )

    seed_sample_sale(cursor)

    conn.commit()
    cursor.close()
    conn.close()


def seed_sample_sale(cursor):
    """Crea una venta de ejemplo si todavía no hay ninguna registrada,
    para que el botón "Ver Detalle" de facturas tenga datos que mostrar."""
    ph = '%s' if USE_MYSQL else '?'

    cursor.execute('SELECT COUNT(*) FROM ventas')
    if cursor.fetchone()[0] > 0:
        return

    cursor.execute('SELECT id_producto, precio_venta FROM productos ORDER BY id_producto LIMIT 2')
    productos = cursor.fetchall()
    if len(productos) < 1:
        return

    cursor.execute('SELECT id_cliente FROM clientes ORDER BY id_cliente LIMIT 1')
    cliente = cursor.fetchone()
    if cliente:
        cliente_id = cliente[0]
    else:
        cursor.execute(
            f'INSERT INTO clientes (nombre, telefono, correo, direccion) VALUES ({ph}, {ph}, {ph}, {ph})',
            ('Juan Pérez', '0412-0000000', 'juan.perez@sublime.com', 'Av. Principal, Local 1')
        )
        cliente_id = cursor.lastrowid

    items = [(prod_id, float(precio), 2 if i == 0 else 1) for i, (prod_id, precio) in enumerate(productos)]
    total = sum(precio * cantidad for _, precio, cantidad in items)

    cursor.execute(
        f'INSERT INTO ventas (id_cliente, total) VALUES ({ph}, {ph})',
        (cliente_id, total)
    )
    venta_id = cursor.lastrowid

    for prod_id, precio, cantidad in items:
        cursor.execute(
            f'INSERT INTO detalle_ventas (id_venta, id_producto, cantidad, precio_unitario) '
            f'VALUES ({ph}, {ph}, {ph}, {ph})',
            (venta_id, prod_id, cantidad, precio)
        )


init_db()


@app.route('/')
def root():
    return redirect('/login/index.html')


@app.route('/admin')
def admin_index():
    return redirect('/admin-panel/index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email y contraseña son requeridos.'}), 400
    
    conn = get_db()
    user = conn.execute(
        'SELECT u.id_usuario, u.nombre, u.correo, u.contraseña, r.nombre AS rol '
        'FROM usuarios u LEFT JOIN roles r ON u.id_rol = r.id_rol WHERE u.correo = ?',
        (email,)
    ).fetchone()
    conn.close()
    
    if not user or user['contraseña'] != password:
        return jsonify({'message': 'Credenciales incorrectas.'}), 401
    
    user_data = {
        'id': user['id_usuario'],
        'nombre': user['nombre'],
        'correo': user['correo'],
        'rol': user['rol'] or 'Trabajador'
    }
    return jsonify({'user': user_data})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    
    if not name or not email or not password:
        return jsonify({'message': 'Nombre, email y contraseña son requeridos.'}), 400
    
    conn = get_db()
    existing = conn.execute('SELECT 1 FROM usuarios WHERE correo = ?', (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({'message': 'El correo ya está registrado.'}), 409
    
    role = conn.execute('SELECT id_rol FROM roles WHERE nombre = ? LIMIT 1', ('Trabajador',)).fetchone()
    role_id = role['id_rol'] if role else 2
    
    conn.execute('INSERT INTO usuarios (nombre, correo, contraseña, id_rol) VALUES (?, ?, ?, ?)',
                (name, email, password, role_id))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Usuario registrado con éxito.'}), 201

@app.route('/api/dashboard', methods=['GET'])
def dashboard():
    conn = get_db()
    
    stats = {}
    stats['totalSales'] = conn.execute('SELECT COUNT(*) AS total FROM ventas').fetchone()['total']
    stats['totalClients'] = conn.execute('SELECT COUNT(*) AS total FROM clientes').fetchone()['total']
    stats['totalProducts'] = conn.execute('SELECT COUNT(*) AS total FROM productos').fetchone()['total']
    stats['totalStock'] = conn.execute('SELECT IFNULL(SUM(stock), 0) AS total FROM productos').fetchone()['total']
    stats['totalIncome'] = conn.execute('SELECT IFNULL(SUM(total), 0) AS total FROM ventas').fetchone()['total']
    
    top_products = conn.execute(
        'SELECT p.nombre AS producto, SUM(d.cantidad) AS cantidad, IFNULL(SUM(d.cantidad * d.precio_unitario), 0) AS total '
        'FROM detalle_ventas d JOIN productos p ON p.id_producto = d.id_producto '
        'GROUP BY p.id_producto ORDER BY cantidad DESC LIMIT 5'
    ).fetchall()
    
    categories = conn.execute(
        'SELECT c.nombre AS categoria, IFNULL(SUM(p.stock), 0) AS stock '
        'FROM categorias c LEFT JOIN productos p ON p.id_categoria = c.id_categoria '
        'GROUP BY c.id_categoria ORDER BY stock DESC LIMIT 5'
    ).fetchall()
    
    monthly = conn.execute(
        "SELECT strftime('%m', fecha) AS mes, IFNULL(SUM(total), 0) AS total "
        'FROM ventas GROUP BY mes ORDER BY mes ASC'
    ).fetchall()
    
    conn.close()
    
    return jsonify({
        'stats': stats,
        'topProducts': [dict(row) for row in top_products],
        'categories': [dict(row) for row in categories],
        'monthly': [dict(row) for row in monthly]
    })

@app.route('/api/inventory', methods=['GET'])
def inventory():
    conn = get_db()
    inventory = conn.execute(
        'SELECT p.id_producto, p.nombre, p.precio_venta AS precio, p.stock, c.nombre AS categoria '
        'FROM productos p LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'ORDER BY p.nombre ASC'
    ).fetchall()
    conn.close()
    return jsonify({'inventory': [dict(row) for row in inventory]})

@app.route('/api/clients', methods=['GET'])
def clients():
    conn = get_db()
    clients = conn.execute(
        'SELECT id_cliente, nombre, correo, telefono, direccion FROM clientes ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'clients': [dict(row) for row in clients]})

@app.route('/api/invoices', methods=['GET'])
def invoices():
    conn = get_db()
    invoices = conn.execute(
        'SELECT v.id_venta AS id, c.nombre AS cliente, v.fecha, COUNT(d.id_detalle) AS items, IFNULL(v.total, 0) AS total '
        'FROM ventas v LEFT JOIN clientes c ON v.id_cliente = c.id_cliente '
        'LEFT JOIN detalle_ventas d ON d.id_venta = v.id_venta '
        'GROUP BY v.id_venta ORDER BY v.fecha DESC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'invoices': [dict(row) for row in invoices]})

@app.route('/api/invoice/<int:invoice_id>', methods=['GET'])
def invoice_detail(invoice_id):
    ph = '%s' if USE_MYSQL else '?'
    conn = get_db()

    venta = conn.execute(
        'SELECT v.id_venta AS id, c.nombre AS cliente, v.fecha, IFNULL(v.total, 0) AS total '
        'FROM ventas v LEFT JOIN clientes c ON v.id_cliente = c.id_cliente '
        f'WHERE v.id_venta = {ph}',
        (invoice_id,)
    ).fetchone()

    if not venta:
        conn.close()
        return jsonify({'message': 'Factura no encontrada.'}), 404

    detalles = conn.execute(
        'SELECT p.nombre AS producto, d.cantidad AS cantidad, '
        'IFNULL(d.precio_unitario, 0) AS precio, '
        'IFNULL(d.cantidad * d.precio_unitario, 0) AS total '
        'FROM detalle_ventas d LEFT JOIN productos p ON d.id_producto = p.id_producto '
        f'WHERE d.id_venta = {ph}',
        (invoice_id,)
    ).fetchall()
    conn.close()

    invoice = dict(venta)
    invoice['detalles'] = [dict(row) for row in detalles]
    return jsonify(invoice)

@app.route('/api/sales-data', methods=['GET'])
def sales_data():
    conn = get_db()
    products = conn.execute(
        'SELECT id_producto, nombre, precio_venta AS precio, stock FROM productos ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    clients = conn.execute(
        'SELECT id_cliente, nombre FROM clientes ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'products': [dict(row) for row in products], 'clients': [dict(row) for row in clients]})

@app.route('/api/recover', methods=['POST'])
def recover_password():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email y nueva contraseña son requeridos.'}), 400

    conn = get_db()
    user = conn.execute(
        'SELECT id_usuario FROM usuarios WHERE correo = ?' if not USE_MYSQL else 'SELECT id_usuario FROM usuarios WHERE correo = %s',
        (email,)
    ).fetchone()

    if not user:
        conn.close()
        return jsonify({'message': 'No se encontró un usuario con ese correo.'}), 404

    if USE_MYSQL:
        conn.execute(
            'UPDATE usuarios SET contraseña = %s WHERE correo = %s',
            (password, email)
        )
    else:
        conn.execute(
            'UPDATE usuarios SET contraseña = ? WHERE correo = ?',
            (password, email)
        )

    conn.commit()
    conn.close()
    return jsonify({'message': 'Contraseña actualizada con éxito.'})

if __name__ == '__main__':
    app.run(debug=True, port=3000)