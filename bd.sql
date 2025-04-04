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
    id_lider1 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    id_lider2 INT REFERENCES usuarios(id_usuario) ON DELETE SET NULL
);