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