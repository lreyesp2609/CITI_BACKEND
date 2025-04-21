INSERT INTO rol (rol, descripcion) VALUES 
('Pastor', 'Usuario con privilegios'),
('Lider', 'Usuario estándar');

BEGIN;

-- Insertar en la tabla personas
INSERT INTO personas (numero_cedula, nombres, apellidos, fecha_nacimiento, genero, celular, direccion, correo_electronico)
VALUES ('1208759348', 'Kerly Mikaela', 'Triana Arrieta', '2002-04-23', 'Femenino', '0981346049', 'Ecuador - Los Rios - Quevedo', 'ktrianaa2@uteq.edu.ec')
RETURNING id_persona;

-- Suponiendo que el id_persona retornado de la inserción anterior es 1
INSERT INTO usuarios (id_rol, id_persona, usuario, contrasenia)
VALUES (1, currval('personas_id_persona_seq'), 'ktrianaa2', 'pbkdf2_sha256$720000$nA1DBiCSy5A4HPTMAfMGDx$MmlhOsKKop+XKgi48HY1WYVShwtU6vD1/nsc8bnk2Zo=');

COMMIT;

-- Insertar estados básicos
INSERT INTO estado_evento (nombre, descripcion) VALUES 
('Pendiente', 'Evento creado y pendiente de aprobación'),
('Aprobado', 'Evento aprobado por los pastores'),
('Rechazado', 'Evento rechazado por los pastores'),
('Cancelado', 'Evento cancelado'),
('Realizado', 'Evento completado satisfactoriamente'),
('Pospuesto', 'Evento pospuesto para otra fecha');

INSERT INTO tipo_evento (nombre, descripcion) VALUES 
('Seminario', 'Evento educativo o de formación'),
('Movilización', 'Evento de acción social o comunitaria'),
('Congreso', 'Evento masivo con múltiples actividades'),
('Conferencia', 'Evento con uno o varios expositores'),
('Taller', 'Evento práctico de aprendizaje');