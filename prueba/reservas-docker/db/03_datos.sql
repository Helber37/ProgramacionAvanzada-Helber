-- Datos de ejemplo para la demo
INSERT INTO edificios (nombre) VALUES ('Bloque de Ingenierías'), ('Centro de Bienestar');

INSERT INTO categorias (nombre) VALUES ('academico'), ('deportivo'), ('recreativo'), ('eventos');

INSERT INTO tipos_espacio (categoria_id, nombre, anticipacion_dias, max_horas) VALUES
    ((SELECT id FROM categorias WHERE nombre='academico'),   'laboratorio',       3, 2),
    ((SELECT id FROM categorias WHERE nombre='academico'),   'sala_computo',      3, 2),
    ((SELECT id FROM categorias WHERE nombre='academico'),   'sala_reuniones',    3, 2),
    ((SELECT id FROM categorias WHERE nombre='deportivo'),   'cancha',            3, 2),
    ((SELECT id FROM categorias WHERE nombre='recreativo'),  'sala_juegos',       3, 2),
    ((SELECT id FROM categorias WHERE nombre='recreativo'),  'zona_bienestar',    3, 2),
    ((SELECT id FROM categorias WHERE nombre='eventos'),     'sala_conferencias', 5, 4);

INSERT INTO espacios (edificio_id, tipo_id, nombre, piso, capacidad, accesible, notas_accesibilidad) VALUES
 (1, (SELECT id FROM tipos_espacio WHERE nombre='laboratorio'),       'Laboratorio de Electrónica', 1, 24, TRUE,  'Rampa de acceso y mesas de altura ajustable'),
 (1, (SELECT id FROM tipos_espacio WHERE nombre='laboratorio'),       'Laboratorio de Física',      2, 20, FALSE, NULL),
 (1, (SELECT id FROM tipos_espacio WHERE nombre='sala_computo'),      'Sala de Cómputo 1',          1, 30, TRUE,  'Ascensor, puestos amplios para silla de ruedas'),
 (1, (SELECT id FROM tipos_espacio WHERE nombre='sala_computo'),      'Sala de Cómputo 2',          3, 30, FALSE, NULL),
 (1, (SELECT id FROM tipos_espacio WHERE nombre='sala_reuniones'),    'Sala de Reuniones A',        1, 10, TRUE,  'Puerta ancha y baño adaptado en el mismo piso'),
 (2, (SELECT id FROM tipos_espacio WHERE nombre='cancha'),            'Cancha de Fútbol Sala',      1, 14, TRUE,  'Acceso sin escalones desde el parqueadero'),
 (2, (SELECT id FROM tipos_espacio WHERE nombre='cancha'),            'Cancha de Baloncesto',       1, 10, FALSE, NULL),
 (2, (SELECT id FROM tipos_espacio WHERE nombre='sala_juegos'),       'Sala de Juegos',             1, 16, TRUE,  'Mesas de altura regulable y rampa'),
 (2, (SELECT id FROM tipos_espacio WHERE nombre='zona_bienestar'),    'Zona de Bienestar',          2, 20, FALSE, NULL),
 (1, (SELECT id FROM tipos_espacio WHERE nombre='sala_conferencias'), 'Sala de Conferencias',       1, 80, TRUE,  'Espacios reservados para sillas de ruedas y bucle auditivo');

-- Módulos reales de laboratorios y salas de cómputo
INSERT INTO modulos (espacio_id, nombre, capacidad)
SELECT e.id, 'Módulo ' || m, 6
FROM espacios e, unnest(ARRAY['A','B','C','D']) AS m
WHERE e.nombre IN ('Laboratorio de Electrónica', 'Laboratorio de Física');

INSERT INTO modulos (espacio_id, nombre, capacidad)
SELECT e.id, 'Zona ' || z, 10
FROM espacios e, unnest(ARRAY['1','2','3']) AS z
WHERE e.nombre IN ('Sala de Cómputo 1', 'Sala de Cómputo 2');

-- Los demás espacios se reservan completos
INSERT INTO modulos (espacio_id, nombre, capacidad)
SELECT id, 'Espacio completo', capacidad FROM espacios
WHERE id NOT IN (SELECT espacio_id FROM modulos);

-- Horario: lunes a sábado, 6:00 a 22:00
INSERT INTO horarios_espacio (espacio_id, dia_semana, apertura, cierre)
SELECT e.id, d, '06:00', '22:00' FROM espacios e, generate_series(1, 6) AS d;

INSERT INTO recursos (nombre) VALUES
    ('Videobeam'), ('Micrófonos'), ('Osciloscopios'), ('Computadores'), ('Balones'), ('Mesa de ping pong'), ('Tablero');

INSERT INTO espacio_recursos (espacio_id, recurso_id, cantidad)
SELECT e.id, r.id, c.cant FROM (VALUES
    ('Laboratorio de Electrónica', 'Osciloscopios', 8),
    ('Sala de Cómputo 1', 'Computadores', 30),
    ('Sala de Cómputo 2', 'Computadores', 30),
    ('Sala de Reuniones A', 'Videobeam', 1),
    ('Sala de Conferencias', 'Videobeam', 2),
    ('Sala de Conferencias', 'Micrófonos', 4),
    ('Cancha de Fútbol Sala', 'Balones', 3),
    ('Sala de Juegos', 'Mesa de ping pong', 2)
) AS c(esp, rec, cant)
JOIN espacios e ON e.nombre = c.esp
JOIN recursos r ON r.nombre = c.rec;

-- Usuario de prueba (correo: demo@universidad.edu.co / contraseña: demo1234)
INSERT INTO usuarios (nombre, correo, password_hash)
VALUES ('Usuario Demo', 'demo@universidad.edu.co', 'scrypt:32768:8:1$oxQw5Nyc05P0D3U5$ceda6e27c457175af01ff2ad7e9dfdf6c007d2b216f5c675639e2489c75307ea41d8e6579beeadd69b14962a46ccbbef778adf83f76c9df0dd67d6dff6e7683c');

-- Una reserva existente (en 4 días) para ver horarios ocupados en la interfaz
WITH r AS (
    INSERT INTO reservas (usuario_id, espacio_id, inicio, fin, motivo, num_asistentes)
    SELECT u.id, e.id,
           (current_date + 4) + time '10:00', (current_date + 4) + time '12:00',
           'Práctica de circuitos', 6
      FROM usuarios u, espacios e
     WHERE u.correo = 'demo@universidad.edu.co' AND e.nombre = 'Laboratorio de Electrónica'
    RETURNING id, inicio, fin
)
INSERT INTO reserva_modulos (reserva_id, modulo_id, inicio, fin)
SELECT r.id, m.id, r.inicio, r.fin
  FROM r, modulos m JOIN espacios e ON e.id = m.espacio_id
 WHERE e.nombre = 'Laboratorio de Electrónica' AND m.nombre = 'Módulo A';
