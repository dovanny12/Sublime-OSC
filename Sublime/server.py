import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'pagina-web-sublime'))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app import app  # noqa: E402

if __name__ == '__main__':
    app.run(debug=True, port=5000)


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
    
    date_function = "DATE_FORMAT(fecha, '%m')" if USE_MYSQL else "strftime('%m', fecha)"
    monthly = conn.execute(
        f'SELECT {date_function} AS mes, IFNULL(SUM(total), 0) AS total '
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
        'SELECT p.id_producto, p.nombre, p.precio_venta AS precio, IFNULL(i.stock_actual, 0) AS stock, c.nombre AS categoria '
        'FROM productos p '
        'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.activo = 1 '
        'ORDER BY p.nombre ASC'
    ).fetchall()
    conn.close()
    return jsonify({'inventory': [dict(row) for row in inventory]})

@app.route('/api/clients', methods=['GET'])
def clients():
    conn = get_db()
    clients = conn.execute(
        'SELECT id_cliente, nombre, correo, telefono, direccion FROM clientes WHERE activo = 1 ORDER BY nombre ASC LIMIT 20'
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
        'SELECT p.id_producto, p.nombre, p.precio_venta AS precio, IFNULL(i.stock_actual, 0) AS stock '
        'FROM productos p '
        'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        'WHERE p.activo = 1 ORDER BY p.nombre ASC LIMIT 20'
    ).fetchall()
    clients = conn.execute(
        'SELECT id_cliente, nombre FROM clientes WHERE activo = 1 ORDER BY nombre ASC LIMIT 20'
    ).fetchall()
    conn.close()
    return jsonify({'products': [dict(row) for row in products], 'clients': [dict(row) for row in clients]})

@app.route('/api/product/<int:product_id>', methods=['GET'])
def get_product(product_id):
    ph = placeholder()
    conn = get_db()
    product = conn.execute(
        f'SELECT p.id_producto, p.nombre, p.descripcion, p.precio_venta AS precio, p.costo, c.id_categoria, c.nombre AS categoria, IFNULL(i.stock_actual, 0) AS stock '
        f'FROM productos p '
        f'LEFT JOIN categorias c ON p.id_categoria = c.id_categoria '
        f'LEFT JOIN inventario i ON i.id_producto = p.id_producto '
        f'WHERE p.id_producto = {ph} AND p.activo = 1',
        (product_id,)
    ).fetchone()
    conn.close()
    if not product:
        return jsonify({'message': 'Producto no encontrado.'}), 404
    return jsonify({'product': dict(product)})

@app.route('/api/product', methods=['POST'])
def create_product():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    categoria = data.get('categoria')
    precio = data.get('precio')
    stock = data.get('stock', 0)
    descripcion = data.get('descripcion', '')

    if not nombre or not categoria or precio is None:
        return jsonify({'message': 'Nombre, categoría y precio son requeridos.'}), 400

    conn = get_db()
    ph = placeholder()
    category_row = conn.execute(
        f'SELECT id_categoria FROM categorias WHERE nombre = {ph} LIMIT 1',
        (categoria,)
    ).fetchone()
    if category_row:
        category_id = category_row['id_categoria']
    else:
        category_cursor = conn.execute(
            f'INSERT INTO categorias (nombre) VALUES ({ph})',
            (categoria,)
        )
        category_id = category_cursor.lastrowid
        if not category_id:
            category_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    product_cursor = conn.execute(
        f'INSERT INTO productos (nombre, descripcion, costo, precio_venta, id_categoria) VALUES ({ph}, {ph}, {ph}, {ph}, {ph})',
        (nombre, descripcion, precio, precio, category_id)
    )
    product_id = product_cursor.lastrowid
    if not product_id:
        product_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    conn.execute(
        f'INSERT INTO inventario (id_producto, stock_actual) VALUES ({ph}, {ph})',
        (product_id, stock)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto creado correctamente.', 'id_producto': product_id}), 201

@app.route('/api/product/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.get_json() or {}
    nombre = data.get('nombre')
    categoria = data.get('categoria')
    precio = data.get('precio')
    stock = data.get('stock')
    descripcion = data.get('descripcion', '')

    if not nombre or not categoria or precio is None or stock is None:
        return jsonify({'message': 'Nombre, categoría, precio y stock son requeridos.'}), 400

    conn = get_db()
    ph = placeholder()
    category_row = conn.execute(
        f'SELECT id_categoria FROM categorias WHERE nombre = {ph} LIMIT 1',
        (categoria,)
    ).fetchone()
    if category_row:
        category_id = category_row['id_categoria']
    else:
        category_cursor = conn.execute(
            f'INSERT INTO categorias (nombre) VALUES ({ph})',
            (categoria,)
        )
        category_id = category_cursor.lastrowid
        if not category_id:
            category_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]

    conn.execute(
        f'UPDATE productos SET nombre = {ph}, descripcion = {ph}, precio_venta = {ph}, id_categoria = {ph} WHERE id_producto = {ph}',
        (nombre, descripcion, precio, category_id, product_id)
    )
    existing_inv = conn.execute(
        f'SELECT id_inventario FROM inventario WHERE id_producto = {ph}',
        (product_id,)
    ).fetchone()
    if existing_inv:
        conn.execute(
            f'UPDATE inventario SET stock_actual = {ph} WHERE id_producto = {ph}',
            (stock, product_id)
        )
    else:
        conn.execute(
            f'INSERT INTO inventario (id_producto, stock_actual) VALUES ({ph}, {ph})',
            (product_id, stock)
        )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto actualizado correctamente.'})

@app.route('/api/product/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    ph = placeholder()
    conn = get_db()
    conn.execute(f'DELETE FROM imagenes_productos WHERE id_producto = {ph}', (product_id,))
    conn.execute(f'DELETE FROM inventario WHERE id_producto = {ph}', (product_id,))
    conn.execute(f'DELETE FROM productos WHERE id_producto = {ph}', (product_id,))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Producto eliminado correctamente.'})

@app.route('/api/client/<int:client_id>', methods=['GET'])
def get_client(client_id):
    ph = placeholder()
    conn = get_db()
    client = conn.execute(
        f'SELECT id_cliente, nombre, correo, telefono, direccion FROM clientes WHERE id_cliente = {ph} AND activo = 1',
        (client_id,)
    ).fetchone()
    conn.close()
    if not client:
        return jsonify({'message': 'Cliente no encontrado.'}), 404
    return jsonify({'client': dict(client)})

@app.route('/api/client', methods=['POST'])
def create_client():
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    telefono = data.get('telefono', '')
    direccion = data.get('direccion', '')

    if not nombre or not correo:
        return jsonify({'message': 'Nombre y correo son requeridos.'}), 400

    conn = get_db()
    ph = placeholder()
    conn.execute(
        f'INSERT INTO clientes (nombre, correo, telefono, direccion, activo) VALUES ({ph}, {ph}, {ph}, {ph}, 1)',
        (nombre, correo, telefono, direccion)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente creado correctamente.'}), 201

@app.route('/api/client/<int:client_id>', methods=['PUT'])
def update_client(client_id):
    data = request.get_json() or {}
    nombre = data.get('nombre')
    correo = data.get('correo')
    telefono = data.get('telefono', '')
    direccion = data.get('direccion', '')

    if not nombre or not correo:
        return jsonify({'message': 'Nombre y correo son requeridos.'}), 400

    ph = placeholder()
    conn = get_db()
    conn.execute(
        f'UPDATE clientes SET nombre = {ph}, correo = {ph}, telefono = {ph}, direccion = {ph} WHERE id_cliente = {ph} AND activo = 1',
        (nombre, correo, telefono, direccion, client_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente actualizado correctamente.'})

@app.route('/api/client/<int:client_id>', methods=['DELETE'])
def delete_client(client_id):
    ph = placeholder()
    conn = get_db()
    conn.execute(
        f'UPDATE clientes SET activo = 0 WHERE id_cliente = {ph}',
        (client_id,)
    )
    conn.commit()
    conn.close()
    return jsonify({'message': 'Cliente eliminado correctamente.'})

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