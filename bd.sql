-- Tabla de roles de usuario
CREATE TABLE rol (
    id_rol SERIAL PRIMARY KEY,
    rol VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255)
);

-- Tabla de personas
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

-- Tabla de usuarios (necesita rol y personas)
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

-- Ministerio (necesita usuarios para líderes)
CREATE TABLE ministerio (
    id_ministerio SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    estado VARCHAR(100),
    imagen_path VARCHAR(255),
    id_lider1 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    id_lider2 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);

-- Tipos de evento (antes que eventos)
CREATE TABLE tipo_evento (
    id_tipo_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion VARCHAR(255),
    activo BOOLEAN DEFAULT TRUE
);

-- Estado de eventos
CREATE TABLE estado_evento (
    id_estado SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    descripcion VARCHAR(255)
);

-- Eventos
CREATE TABLE eventos (
    id_evento SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    id_ministerio INT NOT NULL,
    descripcion TEXT,
    fecha DATE NOT NULL,
    hora TIME NOT NULL,
    lugar VARCHAR(255),
    id_usuario INT NOT NULL, -- creador
    id_estado INT NOT NULL DEFAULT 1,
    id_tipo_evento INT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP,
    FOREIGN KEY (id_ministerio) REFERENCES ministerio(id_ministerio) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    FOREIGN KEY (id_estado) REFERENCES estado_evento(id_estado) ON DELETE SET DEFAULT,
    FOREIGN KEY (id_tipo_evento) REFERENCES tipo_evento(id_tipo_evento) ON DELETE SET NULL
);

-- Motivos de aprobación/rechazo de eventos
CREATE TABLE motivos_evento (
    id_motivo SERIAL PRIMARY KEY,
    id_evento INT NOT NULL,
    id_usuario INT NOT NULL,
    descripcion TEXT NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    hora TIME NOT NULL DEFAULT CURRENT_TIME,
    FOREIGN KEY (id_evento) REFERENCES eventos(id_evento) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

-- Participantes de eventos
CREATE TABLE participantes_evento (
    id_participacion SERIAL PRIMARY KEY,
    id_evento INT NOT NULL,
    id_usuario INT NOT NULL,
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    asistencia BOOLEAN DEFAULT NULL,
    FOREIGN KEY (id_evento) REFERENCES eventos(id_evento) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    UNIQUE (id_evento, id_usuario)
);

-- Notificaciones
CREATE TABLE notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    id_evento INTEGER REFERENCES eventos(id_evento) ON DELETE CASCADE,
    id_usuario_remitente INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_usuario_destino INTEGER REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL, -- 'solicitud_cancelacion', 'aprobacion', 'rechazo'
    mensaje TEXT NOT NULL,
    leida BOOLEAN DEFAULT FALSE,
    fecha_creacion TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    accion_tomada BOOLEAN, -- TRUE=aprobada, FALSE=rechazada, NULL=pendiente
    motivo_rechazo TEXT
);

-- Tabla de ciclos
CREATE TABLE ciclo (
    id_ciclo SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT
);

-- Cursos (necesita ciclo y usuario)
CREATE TABLE curso (
    id_curso SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    fecha_inicio DATE,
    fecha_fin DATE,
    hora_inicio TIME,
    hora_fin TIME,
    id_ciclo INT REFERENCES ciclo(id_ciclo) ON DELETE SET NULL,
    id_usuario INT NOT NULL,
    FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE
);

-- Participantes de cursos
CREATE TABLE curso_participante (
    id_participante SERIAL PRIMARY KEY,
    id_curso INT NOT NULL,
    id_persona INT NOT NULL,
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_curso) REFERENCES curso(id_curso) ON DELETE CASCADE,
    FOREIGN KEY (id_persona) REFERENCES personas(id_persona) ON DELETE CASCADE,
    UNIQUE (id_curso, id_persona)
);

-- Asistencia a cursos
CREATE TABLE asistencia_curso (
    id_asistencia SERIAL PRIMARY KEY,
    id_curso INT NOT NULL,
    id_persona INT NOT NULL,
    fecha DATE NOT NULL,
    presente BOOLEAN NOT NULL,
    FOREIGN KEY (id_curso) REFERENCES curso(id_curso) ON DELETE CASCADE,
    FOREIGN KEY (id_persona) REFERENCES personas(id_persona) ON DELETE CASCADE
);

-- Rúbricas de evaluación
CREATE TABLE rubrica (
    id_rubrica SERIAL PRIMARY KEY,
    id_curso INT NOT NULL,
    nombre_criterio VARCHAR(100) NOT NULL,
    porcentaje NUMERIC(5,2) NOT NULL CHECK (porcentaje >= 0 AND porcentaje <= 100),
    FOREIGN KEY (id_curso) REFERENCES curso(id_curso) ON DELETE CASCADE
);

-- Tareas de cursos
CREATE TABLE tarea (
    id_tarea SERIAL PRIMARY KEY,
    id_curso INT NOT NULL,
    id_criterio INT NOT NULL,
    titulo VARCHAR(255) NOT NULL,
    descripcion TEXT,
    fecha_entrega DATE,
    FOREIGN KEY (id_curso) REFERENCES curso(id_curso) ON DELETE CASCADE,
    FOREIGN KEY (id_criterio) REFERENCES rubrica(id_rubrica) ON DELETE CASCADE
);

-- Calificaciones de tareas
CREATE TABLE calificacion (
    id_calificacion SERIAL PRIMARY KEY,
    id_tarea INT NOT NULL,
    id_persona INT NOT NULL,
    nota NUMERIC(5,2) NOT NULL CHECK (nota >= 0 AND nota <= 10),
    FOREIGN KEY (id_tarea) REFERENCES tarea(id_tarea) ON DELETE CASCADE,
    FOREIGN KEY (id_persona) REFERENCES personas(id_persona) ON DELETE CASCADE,
    UNIQUE (id_tarea, id_persona)
);

-- Devocionales
CREATE TABLE devocionales (
    id_devocional SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    mes VARCHAR(20) NOT NULL,
    año INTEGER NOT NULL,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    titulo TEXT NOT NULL,
    texto_biblico TEXT NOT NULL,
    reflexion TEXT NOT NULL,
    contenido_calendario JSONB,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
