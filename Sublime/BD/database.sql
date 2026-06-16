-- =========================================================
-- DATABASE.SQL
-- TIENDA DE SUBLIMACIÓN - SISTEMA COMPLETO 4FN
-- =========================================================

PRAGMA foreign_keys = ON;

-- =========================================================
-- ROLES
-- =========================================================

CREATE TABLE roles (
    id_rol INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- =========================================================
-- USUARIOS
-- =========================================================

CREATE TABLE usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(100) NOT NULL UNIQUE,
    contraseña TEXT NOT NULL,
    id_rol INTEGER NOT NULL,
    activo INTEGER DEFAULT 1,

    FOREIGN KEY (id_rol)
    REFERENCES roles(id_rol)
);

-- =========================================================
-- SESIONES LOGIN
-- =========================================================

CREATE TABLE sesiones (
    id_sesion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_usuario INTEGER NOT NULL,
    token TEXT NOT NULL,
    fecha_inicio DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion DATETIME,

    FOREIGN KEY (id_usuario)
    REFERENCES usuarios(id_usuario)
);

-- =========================================================
-- CLIENTES
-- =========================================================

CREATE TABLE clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    telefono VARCHAR(20),
    correo VARCHAR(100) UNIQUE,
    contraseña TEXT,
    direccion TEXT,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    activo INTEGER DEFAULT 1
);

-- =========================================================
-- DIRECCIONES CLIENTES
-- =========================================================

CREATE TABLE direcciones_cliente (
    id_direccion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    direccion TEXT NOT NULL,
    ciudad VARCHAR(100),
    estado VARCHAR(100),
    codigo_postal VARCHAR(20),

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente)
);

-- =========================================================
-- PROVEEDORES
-- =========================================================

CREATE TABLE proveedores (
    id_proveedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    contacto VARCHAR(100),
    telefono VARCHAR(20),
    correo VARCHAR(100),
    direccion TEXT
);

-- =========================================================
-- CATEGORÍAS
-- =========================================================

CREATE TABLE categorias (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL UNIQUE
);

-- =========================================================
-- TASAS DE CAMBIO
-- =========================================================

CREATE TABLE tasas_cambio (
    id_tasa INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    tasa DECIMAL(12,4) NOT NULL,
    fuente VARCHAR(100),
    activa INTEGER DEFAULT 1
);

-- =========================================================
-- PRODUCTOS
-- =========================================================

CREATE TABLE productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    costo DECIMAL(10,2) NOT NULL,
    precio_venta DECIMAL(10,2) NOT NULL,
    id_categoria INTEGER NOT NULL,
    activo INTEGER DEFAULT 1,

    FOREIGN KEY (id_categoria)
    REFERENCES categorias(id_categoria)
);


-- =========================================================
-- IMÁGENES PRODUCTOS
-- =========================================================

CREATE TABLE imagenes_productos (
    id_imagen INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    ruta_imagen TEXT NOT NULL,

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- INVENTARIO
-- =========================================================

CREATE TABLE inventario (
    id_inventario INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL UNIQUE,
    stock_actual INTEGER DEFAULT 0,
    stock_minimo INTEGER DEFAULT 5,

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- MOVIMIENTOS INVENTARIO
-- =========================================================

CREATE TABLE movimientos_inventario (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    cantidad INTEGER NOT NULL,
    descripcion TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- ALERTAS
-- =========================================================

CREATE TABLE alertas (
    id_alerta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_producto INTEGER NOT NULL,
    mensaje TEXT NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- FAVORITOS
-- =========================================================

CREATE TABLE favoritos (
    id_favorito INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- CARRITO
-- =========================================================

CREATE TABLE carrito (
    id_carrito INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente)
);

-- =========================================================
-- DETALLE CARRITO
-- =========================================================

CREATE TABLE detalle_carrito (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_carrito INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DECIMAL(10,2),

    FOREIGN KEY (id_carrito)
    REFERENCES carrito(id_carrito),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- PERSONALIZACIÓN CARRITO
-- =========================================================

CREATE TABLE personalizacion_carrito (
    id_personalizacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_detalle_carrito INTEGER NOT NULL,
    descripcion TEXT,

    FOREIGN KEY (id_detalle_carrito)
    REFERENCES detalle_carrito(id_detalle)
);

-- =========================================================
-- IMÁGENES PERSONALIZACIÓN CARRITO
-- =========================================================

CREATE TABLE imagenes_personalizacion_carrito (
    id_imagen INTEGER PRIMARY KEY AUTOINCREMENT,
    id_personalizacion INTEGER NOT NULL,
    ruta_imagen TEXT NOT NULL,

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizacion_carrito(id_personalizacion)
);

-- =========================================================
-- TEXTOS PERSONALIZACIÓN CARRITO
-- =========================================================

CREATE TABLE textos_personalizacion_carrito (
    id_texto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_personalizacion INTEGER NOT NULL,
    texto TEXT,

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizacion_carrito(id_personalizacion)
);

-- =========================================================
-- ESTADOS PEDIDOS
-- =========================================================

CREATE TABLE estados_pedido (
    id_estado INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- =========================================================
-- PEDIDOS
-- =========================================================

CREATE TABLE pedidos (
    id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    id_estado INTEGER NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2),

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente),

    FOREIGN KEY (id_estado)
    REFERENCES estados_pedido(id_estado)
);

-- =========================================================
-- DETALLE PEDIDOS
-- =========================================================

CREATE TABLE detalle_pedidos (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DECIMAL(10,2),

    FOREIGN KEY (id_pedido)
    REFERENCES pedidos(id_pedido),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- PERSONALIZACIONES
-- =========================================================

CREATE TABLE personalizaciones (
    id_personalizacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_detalle_pedido INTEGER NOT NULL,
    descripcion TEXT,

    FOREIGN KEY (id_detalle_pedido)
    REFERENCES detalle_pedidos(id_detalle)
);

-- =========================================================
-- IMÁGENES PERSONALIZACIÓN
-- =========================================================

CREATE TABLE imagenes_personalizacion (
    id_imagen INTEGER PRIMARY KEY AUTOINCREMENT,
    id_personalizacion INTEGER NOT NULL,
    ruta_imagen TEXT NOT NULL,

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizaciones(id_personalizacion)
);

-- =========================================================
-- TEXTOS PERSONALIZACIÓN
-- =========================================================

CREATE TABLE textos_personalizacion (
    id_texto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_personalizacion INTEGER NOT NULL,
    texto TEXT,

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizaciones(id_personalizacion)
);

-- =========================================================
-- ENVÍOS
-- =========================================================

CREATE TABLE envios (
    id_envio INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido INTEGER NOT NULL,
    direccion_envio TEXT,
    empresa_envio VARCHAR(100),
    numero_guia VARCHAR(100),
    estado_envio VARCHAR(50),
    fecha_envio DATETIME,

    FOREIGN KEY (id_pedido)
    REFERENCES pedidos(id_pedido)
);

-- =========================================================
-- VENTAS
-- =========================================================

CREATE TABLE ventas (
    id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2),

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente)
);

-- =========================================================
-- DETALLE VENTAS
-- =========================================================

CREATE TABLE detalle_ventas (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    precio_unitario DECIMAL(10,2),

    FOREIGN KEY (id_venta)
    REFERENCES ventas(id_venta),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- MÉTODOS PAGO
-- =========================================================

CREATE TABLE metodos_pago (
    id_metodo_pago INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- =========================================================
-- PAGOS VENTA
-- =========================================================

CREATE TABLE pagos_venta (
    id_pago INTEGER PRIMARY KEY AUTOINCREMENT,
    id_venta INTEGER NOT NULL,
    id_metodo_pago INTEGER NOT NULL,
    monto DECIMAL(10,2),
    referencia TEXT,

    FOREIGN KEY (id_venta)
    REFERENCES ventas(id_venta),

    FOREIGN KEY (id_metodo_pago)
    REFERENCES metodos_pago(id_metodo_pago)
);

-- =========================================================
-- VERIFICACIÓN PAGOS
-- =========================================================

CREATE TABLE verificaciones_pago (
    id_verificacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pago INTEGER NOT NULL,
    comprobante TEXT,
    estado VARCHAR(50),
    fecha_verificacion DATETIME,

    FOREIGN KEY (id_pago)
    REFERENCES pagos_venta(id_pago)
);

-- =========================================================
-- FACTURAS
-- =========================================================

CREATE TABLE facturas (
    id_factura INTEGER PRIMARY KEY AUTOINCREMENT,

    id_venta INTEGER NOT NULL UNIQUE,

    id_tasa INTEGER,

    numero_factura VARCHAR(50) UNIQUE,

    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    subtotal DECIMAL(10,2),

    porcentaje_iva DECIMAL(5,2),

    impuesto DECIMAL(10,2),

    total_usd DECIMAL(10,2),

    total_bs DECIMAL(12,2),

    FOREIGN KEY (id_venta)
    REFERENCES ventas(id_venta),

    FOREIGN KEY (id_tasa)
    REFERENCES tasas_cambio(id_tasa)
);

-- =========================================================
-- COMPRAS
-- =========================================================

CREATE TABLE compras (
    id_compra INTEGER PRIMARY KEY AUTOINCREMENT,
    id_proveedor INTEGER NOT NULL,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,
    total DECIMAL(10,2),

    FOREIGN KEY (id_proveedor)
    REFERENCES proveedores(id_proveedor)
);

-- =========================================================
-- DETALLE COMPRAS
-- =========================================================

CREATE TABLE detalle_compras (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
    id_compra INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    cantidad INTEGER NOT NULL,
    costo_unitario DECIMAL(10,2),

    FOREIGN KEY (id_compra)
    REFERENCES compras(id_compra),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- CUPONES
-- =========================================================

CREATE TABLE cupones (
    id_cupon INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo VARCHAR(50) UNIQUE,
    descuento DECIMAL(10,2),
    fecha_expiracion DATETIME,
    activo INTEGER DEFAULT 1
);

-- =========================================================
-- RESEÑAS
-- =========================================================

CREATE TABLE reseñas (
    id_reseña INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    id_producto INTEGER NOT NULL,
    comentario TEXT,
    calificacion INTEGER,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente),

    FOREIGN KEY (id_producto)
    REFERENCES productos(id_producto)
);

-- =========================================================
-- NOTIFICACIONES
-- =========================================================

CREATE TABLE notificaciones (
    id_notificacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cliente INTEGER NOT NULL,
    mensaje TEXT,
    leida INTEGER DEFAULT 0,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (id_cliente)
    REFERENCES clientes(id_cliente)
);

-- =========================================================
-- CAJA
-- =========================================================

CREATE TABLE caja (
    id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo VARCHAR(20),
    monto DECIMAL(10,2),
    descripcion TEXT,
    fecha DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- =========================================================
-- SERVICIOS DE PERSONALIZACIÓN
-- =========================================================

CREATE TABLE servicios_personalizacion (
    id_servicio INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio_usd DECIMAL(10,2) NOT NULL,
    activo INTEGER DEFAULT 1
);

-- =========================================================
-- SERVICIOS DE PERSONALIZACIÓN
-- =========================================================

CREATE TABLE servicios_personalizacion (
    id_servicio INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio_usd DECIMAL(10,2) NOT NULL,
    activo INTEGER DEFAULT 1
);

-- =========================================================
-- DETALLE PERSONALIZACIÓN
-- =========================================================

CREATE TABLE detalle_personalizacion (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,

    id_personalizacion INTEGER NOT NULL,

    id_servicio INTEGER NOT NULL,

    cantidad INTEGER DEFAULT 1,

    precio_unitario DECIMAL(10,2),

    subtotal DECIMAL(10,2),

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizaciones(id_personalizacion),

    FOREIGN KEY (id_servicio)
    REFERENCES servicios_personalizacion(id_servicio)
);

-- =========================================================
-- DETALLE DISEÑO
-- =========================================================

CREATE TABLE detalle_diseno (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,

    id_personalizacion INTEGER NOT NULL,

    id_diseno INTEGER NOT NULL,

    precio DECIMAL(10,2),

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizaciones(id_personalizacion),

    FOREIGN KEY (id_diseno)
    REFERENCES servicios_diseno(id_diseno)
);

-- =========================================================
-- DETALLE DISEÑO
-- =========================================================

CREATE TABLE detalle_diseno (
    id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,

    id_personalizacion INTEGER NOT NULL,

    id_diseno INTEGER NOT NULL,

    precio DECIMAL(10,2),

    FOREIGN KEY (id_personalizacion)
    REFERENCES personalizaciones(id_personalizacion),

    FOREIGN KEY (id_diseno)
    REFERENCES servicios_diseno(id_diseno)
);

-- =========================================================
-- CONFIGURACIÓN GENERAL
-- =========================================================

CREATE TABLE configuracion (
    id_configuracion INTEGER PRIMARY KEY AUTOINCREMENT,

    iva_default DECIMAL(5,2) DEFAULT 16,

    moneda_principal VARCHAR(10) DEFAULT 'USD',

    tasa_actual DECIMAL(12,4)
);

-- =========================================================
-- TRIGGERS
-- =========================================================

-- =========================================================
-- EVITAR STOCK NEGATIVO
-- =========================================================

CREATE TRIGGER evitar_stock_negativo
BEFORE INSERT ON detalle_ventas
FOR EACH ROW
BEGIN

    SELECT CASE
        WHEN (
            SELECT stock_actual
            FROM inventario
            WHERE id_producto = NEW.id_producto
        ) < NEW.cantidad

        THEN RAISE(ABORT, 'Stock insuficiente')
    END;

END;

-- =========================================================
-- DESCONTAR STOCK VENTA
-- =========================================================

CREATE TRIGGER disminuir_stock_venta
AFTER INSERT ON detalle_ventas
FOR EACH ROW
BEGIN

    UPDATE inventario
    SET stock_actual = stock_actual - NEW.cantidad
    WHERE id_producto = NEW.id_producto;

    INSERT INTO movimientos_inventario (
        id_producto,
        tipo,
        cantidad,
        descripcion
    )
    VALUES (
        NEW.id_producto,
        'salida',
        NEW.cantidad,
        'Venta realizada'
    );

END;

-- =========================================================
-- AUMENTAR STOCK COMPRA
-- =========================================================

CREATE TRIGGER aumentar_stock_compra
AFTER INSERT ON detalle_compras
FOR EACH ROW
BEGIN

    UPDATE inventario
    SET stock_actual = stock_actual + NEW.cantidad
    WHERE id_producto = NEW.id_producto;

    INSERT INTO movimientos_inventario (
        id_producto,
        tipo,
        cantidad,
        descripcion
    )
    VALUES (
        NEW.id_producto,
        'entrada',
        NEW.cantidad,
        'Compra realizada'
    );

END;

-- =========================================================
-- ALERTA STOCK BAJO
-- =========================================================

CREATE TRIGGER alerta_stock_bajo
AFTER UPDATE ON inventario
FOR EACH ROW
WHEN NEW.stock_actual <= NEW.stock_minimo
BEGIN

    INSERT INTO alertas (
        id_producto,
        mensaje
    )
    VALUES (
        NEW.id_producto,
        'Stock bajo del mínimo permitido'
    );

END;