-- Reglas que dbdiagram no exporta: validaciones y control de concurrencia
ALTER TABLE usuarios         ADD CHECK (rol IN ('estudiante', 'docente', 'administrativo', 'admin'));
ALTER TABLE tipos_espacio    ADD CHECK (anticipacion_dias >= 0), ADD CHECK (max_horas > 0);
ALTER TABLE espacios         ADD CHECK (capacidad > 0);
ALTER TABLE horarios_espacio ADD CHECK (dia_semana BETWEEN 1 AND 7), ADD CHECK (cierre > apertura);
ALTER TABLE cierres_espacio  ADD CHECK (fin > inicio);
ALTER TABLE modulos          ADD CHECK (capacidad > 0);
ALTER TABLE reservas         ADD CHECK (fin > inicio), ADD CHECK (estado IN ('confirmada', 'cancelada'));
ALTER TABLE notificaciones   ADD CHECK (tipo IN ('confirmacion', 'cancelacion', 'recordatorio')),
                             ADD CHECK (estado IN ('pendiente', 'enviada', 'fallida'));

-- CONCURRENCIA: PostgreSQL rechaza dos reservas del mismo módulo en horarios que se cruzan
ALTER TABLE reserva_modulos ADD CHECK (fin > inicio);
ALTER TABLE reserva_modulos ADD EXCLUDE USING gist (modulo_id WITH =, tsrange(inicio, fin) WITH &&);
