CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    rol VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255)
);

CREATE TABLE personas (
    id_persona SERIAL PRIMARY KEY,
    numero_cedula VARCHAR(20) NULL UNIQUE,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NULL,
    genero VARCHAR(20) NULL,
    celular VARCHAR(20) NULL,
    direccion VARCHAR(255) NULL,
    correo_electronico VARCHAR(100) NULL,
    nivel_estudio VARCHAR(50) NULL,
    numero_telefono VARCHAR(15) NULL,
    nacionalidad VARCHAR(30) NULL,
    profesion VARCHAR(50) NULL,
    estado_civil VARCHAR(20) NULL,
    lugar_trabajo VARCHAR(50) NULL
);

CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    id_rol INT NOT NULL,
    id_persona INT NOT NULL,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasenia VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (id_rol) REFERENCES rol(id_rol) ON DELETE CASCADE,
    FOREIGN KEY (id_persona) REFERENCES personas(id_persona) ON DELETE CASCADE
);

CREATE TABLE ministerio (
    id_ministerio SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    estado VARCHAR(100),
    imagen_path VARCHAR(255),
    id_lider1 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    id_lider2 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);

-- Tabla de estados para eventos
CREATE TABLE estado_evento (
    id_estado SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255)
);

-- Tabla principal de eventos
CREATE TABLE eventos (
    id_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    id_ministerio INT NOT NULL,
    descripcion TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    lugar VARCHAR(255),
    id_usuario INT NOT NULL, -- Que crea el evento
    id_estado INT NOT NULL DEFAULT 1, -- Por defecto Pendiente
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    FOREIGN KEY (id_ministerio) REFERENCES ministerio(id_ministerio) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_estado) REFERENCES estado_evento(id_estado) ON DELETE SET DEFAULT,
    FOREIGN KEY (id_tipo_evento) REFERENCES tipo_evento(id_tipo_evento) ON DELETE SET NULL
);

-- Tabla de motivos para eventos (aprobaciones/rechazos)
CREATE TABLE motivos_evento (
    id_motivo SERIAL PRIMARY KEY,
    id_evento INT NOT NULL,
    id_usuario INT NOT NULL, -- Usuario que aprueba/rechaza
    descripcion TEXT NOT NULL, -- Motivo de aprobación/rechazo
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME,
    FOREIGN KEY (id_evento) REFERENCES eventos(id_evento) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

-- Tabla para registro de participantes en eventos
CREATE TABLE participantes_evento (
    id_participacion SERIAL PRIMARY KEY,
    id_evento INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    asistencia BOOLEAN DEFAULT NULL, -- NULL=no confirmado, TRUE=asistió, FALSE=no asistió
    FOREIGN KEY (id_evento) REFERENCES eventos(id_evento) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    UNIQUE (id_evento, id_usuario) -- Un usuario solo puede registrarse una vez por evento
);

CREATE TABLE notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
    id_usuario_remitente INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_usuario_destino INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL, -- 'solicitud_cancelacion', 'aprobacion', 'rechazo'
    mensaje TEXT NOT NULL,
    leida BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accion_tomada BOOLEAN -- TRUE=aprobada, FALSE=rechazada, NULL=pendiente
);

CREATE TABLE tipo_evento (
    id_tipo_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE
);