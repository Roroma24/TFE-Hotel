-- Creación de la base de datos
CREATE DATABASE hotel_delfino;
-- Usar la base de datos
USE hotel_delfino;

-- Tabla de Roles
CREATE TABLE ROLES (
    id_rol INT PRIMARY KEY AUTO_INCREMENT,
    nombre_rol VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255)
);

-- Tipos de habitación
CREATE TABLE TIPOS_HABITACION (
    id_tipo_habitacion INT PRIMARY KEY AUTO_INCREMENT,
    nombre_tipo VARCHAR(100) NOT NULL,
    descripcion TEXT,
    capacidad INT NOT NULL,
    precio_base DECIMAL(10,2) NOT NULL
);

-- Empresas
CREATE TABLE EMPRESAS (
    id_empresa INT PRIMARY KEY AUTO_INCREMENT,
    nombre_empresa VARCHAR(150) NOT NULL,
    direccion VARCHAR(255),
    telefono VARCHAR(50),
    correo VARCHAR(100)
);

-- Usuarios
CREATE TABLE USUARIOS (
    id_usuario INT PRIMARY KEY AUTO_INCREMENT,
    id_rol INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    usuario VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    estado VARCHAR(50),
    FOREIGN KEY (id_rol) REFERENCES ROLES(id_rol)
);

-- Habitaciones
CREATE TABLE HABITACIONES (
    id_habitacion INT PRIMARY KEY AUTO_INCREMENT,
    id_tipo_habitacion INT NOT NULL,
    numero VARCHAR(20) UNIQUE NOT NULL,
    piso VARCHAR(20),
    estado VARCHAR(50),
    observaciones TEXT,
    FOREIGN KEY (id_tipo_habitacion) REFERENCES TIPOS_HABITACION(id_tipo_habitacion)
);

-- Clientes
CREATE TABLE CLIENTES (
    id_cliente INT PRIMARY KEY AUTO_INCREMENT,
    id_empresa INT,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    documento_identidad VARCHAR(50) UNIQUE,
    telefono VARCHAR(50),
    correo VARCHAR(100),
    direccion VARCHAR(255),
    tipo_cliente VARCHAR(50),
    FOREIGN KEY (id_empresa) REFERENCES EMPRESAS(id_empresa)
);

-- Reservas
CREATE TABLE RESERVAS (
    id_reserva INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    id_habitacion INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_reserva DATE NOT NULL,
    fecha_entrada DATE NOT NULL,
    fecha_salida DATE NOT NULL,
    cantidad_huespedes INT NOT NULL,
    estado_reserva VARCHAR(50),
    total_estimado DECIMAL(10,2),
    FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente),
    FOREIGN KEY (id_habitacion) REFERENCES HABITACIONES(id_habitacion),
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

-- Check-in
CREATE TABLE CHECKIN (
    id_checkin INT PRIMARY KEY AUTO_INCREMENT,
    id_reserva INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_hora_checkin DATETIME NOT NULL,
    observaciones TEXT,
    FOREIGN KEY (id_reserva) REFERENCES RESERVAS(id_reserva),
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

-- Check-out
CREATE TABLE CHECKOUT (
    id_checkout INT PRIMARY KEY AUTO_INCREMENT,
    id_reserva INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_hora_checkout DATETIME NOT NULL,
    observaciones TEXT,
    cargos_adicionales DECIMAL(10,2),
    FOREIGN KEY (id_reserva) REFERENCES RESERVAS(id_reserva),
    FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);

-- Facturas
CREATE TABLE FACTURAS (
    id_factura INT PRIMARY KEY AUTO_INCREMENT,
    id_reserva INT NOT NULL,
    id_cliente INT NOT NULL,
    fecha_factura DATE NOT NULL,
    subtotal DECIMAL(10,2) NOT NULL,
    impuestos DECIMAL(10,2) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    estado_factura VARCHAR(50),
    FOREIGN KEY (id_reserva) REFERENCES RESERVAS(id_reserva),
    FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente)
);

-- Servicios
CREATE TABLE SERVICIOS (
    id_servicio INT PRIMARY KEY AUTO_INCREMENT,
    nombre_servicio VARCHAR(100) NOT NULL,
    descripcion TEXT,
    costo DECIMAL(10,2) NOT NULL,
    fecha_servicio DATETIME NOT NULL
);

-- Pagos
CREATE TABLE PAGOS (
    id_pago INT PRIMARY KEY AUTO_INCREMENT,
    id_factura INT NOT NULL,
    fecha_pago DATE NOT NULL,
    monto DECIMAL(10,2) NOT NULL,
    referencia VARCHAR(100),
    estado_pago VARCHAR(50),
    FOREIGN KEY (id_factura) REFERENCES FACTURAS(id_factura)
);

ALTER TABLE PAGOS
ADD COLUMN titular VARCHAR(150),
ADD COLUMN ultimos_4 VARCHAR(4),
ADD COLUMN tipo_tarjeta VARCHAR(20);

CREATE TABLE TARJETAS_CLIENTE (
    id_tarjeta INT PRIMARY KEY AUTO_INCREMENT,
    id_cliente INT NOT NULL,
    titular VARCHAR(150) NOT NULL,
    numero_enmascarado VARCHAR(25) NOT NULL,
    ultimos_4 VARCHAR(4) NOT NULL,
    vencimiento VARCHAR(10) NOT NULL,
    fecha_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente)
);


-- Insertar roles iniciales
INSERT INTO ROLES (id_rol, nombre_rol, descripcion) VALUES
(1, 'cliente', 'Usuarios que buscan reservar en el hotel'),
(2, 'recepcionista', 'Personal que atiende en instalaciones físicas'),
(3, 'gerente', 'Personal que gestiona el hotel');

-- Insertar empresas
INSERT INTO EMPRESAS
(nombre_empresa, direccion, telefono, correo)
VALUES
(
    'Tech Solutions MX',
    'Av. Reforma 1200, Ciudad de México',
    '5551234567',
    'contacto@techsolutions.com'
),
(
    'Grupo Empresarial Rivera',
    'Blvd. Costero 45, Cancún',
    '9984567890',
    'reservas@rivera.com'
),
(
    'Corporativo Delfino',
    'Paseo del Mar 88, Los Cabos',
    '6247891234',
    'admin@delfino.com'
);
