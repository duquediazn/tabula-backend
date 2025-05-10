-- CREACIÓN DE LAS TABLAS
-- Tabla de Usuarios
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    passwd VARCHAR(255) NOT NULL,
    rol VARCHAR(50) CHECK (rol IN ('usuario', 'admin')),
    activo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabla de Almacenes
CREATE TABLE almacen (
    codigo SERIAL PRIMARY KEY,
    descripcion VARCHAR(255) NOT NULL,
    activo BOOLEAN DEFAULT TRUE NOT NULL
);

-- Tabla de Categorías de Productos
CREATE TABLE categoria_producto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE
);

-- Tabla de Productos
CREATE TABLE producto (
    codigo SERIAL PRIMARY KEY, 
    sku VARCHAR(20) UNIQUE NOT NULL, 
    nombre_corto VARCHAR(100) NOT NULL,
    descripcion VARCHAR(500),
    id_categoria INTEGER NOT NULL, 
    activo BOOLEAN DEFAULT TRUE NOT NULL,
    FOREIGN KEY (id_categoria) REFERENCES categoria_producto(id)
);

-- Tabla de Movimientos
CREATE TABLE movimientos (
    id_mov SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT NOW(),
    tipo VARCHAR(10) CHECK (tipo IN ('entrada', 'salida')),
    id_usuario INT NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuario(id) 
);

-- Tabla de Movimientos_Líneas
CREATE TABLE movimientos_lineas (
    id_mov INT NOT NULL, 
    id_linea INT NOT NULL CHECK (id_linea > 0),  
    codigo_almacen INT NOT NULL,
    codigo_producto INT NOT NULL,
    lote VARCHAR(50) DEFAULT 'SIN_LOTE',
    fecha_cad DATE,
    cantidad INT NOT NULL CHECK (cantidad > 0),
    PRIMARY KEY (id_mov, id_linea),  
    FOREIGN KEY (id_mov) REFERENCES movimientos(id_mov),
    FOREIGN KEY (codigo_almacen) REFERENCES almacen(codigo),
    FOREIGN KEY (codigo_producto) REFERENCES producto(codigo)
);


-- Tabla de Stock
CREATE TABLE stock (
    codigo_almacen INT REFERENCES almacen(codigo) ON DELETE RESTRICT,
    codigo_producto INT REFERENCES producto(codigo) ON DELETE RESTRICT,
    lote VARCHAR(50) DEFAULT 'SIN_LOTE',
    fecha_cad DATE,
    cantidad INT CHECK (cantidad >= 0),
    PRIMARY KEY (codigo_almacen, codigo_producto, lote) 
);

-- CREACIÓN DE LA FUNCIÓN actualizar_stock() 
CREATE OR REPLACE FUNCTION actualizar_stock() RETURNS TRIGGER AS $$
DECLARE 
    tipo_movimiento VARCHAR(10);
    usuario_movimiento INT;
    lote_procesado VARCHAR(50);
BEGIN
    -- Obtener el tipo de movimiento y el usuario que lo realizó
    SELECT tipo, id_usuario INTO tipo_movimiento, usuario_movimiento 
    FROM movimientos 
    WHERE id_mov = NEW.id_mov;

    -- Si no se especifica lote, asignar 'SIN_LOTE'
    lote_procesado := COALESCE(NEW.lote, 'SIN_LOTE'); -- Reemplaza NULL por 'SIN LOTE'

    -- Si el lote procesado es 'SIN_LOTE' y se introduce fecha de caducidad, levantamos excepción.
	IF lote_procesado = 'SIN_LOTE' AND NEW.fecha_cad IS NOT NULL THEN
		RAISE EXCEPTION 'No se puede poner fecha de caducidad a un producto sin lote'; 
	END IF;
	
    -- Si el lote procesado tiene lote, pero ya existe ese lote con otra fecha, levantamos excepción. 
	IF lote_procesado <> 'SIN_LOTE' AND (
		SELECT COUNT(*) FROM stock WHERE codigo_almacen = NEW.codigo_almacen 
                                      AND codigo_producto = NEW.codigo_producto
                                      AND lote = lote_procesado
									  AND fecha_cad <> NEW.fecha_cad) > 0 THEN
		  RAISE EXCEPTION 'Ya existe el lote % con otra fecha', lote_procesado;
	  END IF;

    -- Si es una entrada, sumamos la cantidad al stock
    IF tipo_movimiento = 'entrada' THEN
        INSERT INTO stock (codigo_almacen, codigo_producto, lote, fecha_cad, cantidad)
        VALUES (NEW.codigo_almacen, NEW.codigo_producto, lote_procesado, NEW.fecha_cad, NEW.cantidad)
        ON CONFLICT (codigo_almacen, codigo_producto, lote)
        DO UPDATE SET cantidad = stock.cantidad + NEW.cantidad;

    -- Si es una salida, restamos la cantidad al stock
    ELSIF tipo_movimiento = 'salida' THEN

        -- Verificamos que haya stock suficiente antes de restar
        IF (SELECT cantidad FROM stock WHERE codigo_almacen = NEW.codigo_almacen 
                                      AND codigo_producto = NEW.codigo_producto
                                      AND lote = lote_procesado) < NEW.cantidad OR 
			(SELECT COUNT(*) FROM stock WHERE codigo_almacen = NEW.codigo_almacen 
                                      AND codigo_producto = NEW.codigo_producto
                                      AND lote = lote_procesado) = 0
									  THEN
            RAISE EXCEPTION 'Stock insuficiente para el producto % en el almacén % con lote %', 
                            NEW.codigo_producto, NEW.codigo_almacen, lote_procesado;
        END IF;

        -- Restamos la cantidad al stock
        UPDATE stock
        SET cantidad = GREATEST(0, cantidad - NEW.cantidad)
        WHERE codigo_almacen = NEW.codigo_almacen 
          AND codigo_producto = NEW.codigo_producto
          AND lote = lote_procesado;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- CREACIÓN DEL TRIGGER 
CREATE TRIGGER trg_actualizar_stock
AFTER INSERT ON movimientos_lineas
FOR EACH ROW
EXECUTE FUNCTION actualizar_stock();
