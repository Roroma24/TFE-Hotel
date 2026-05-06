# Sistema de Gestión de Hotel

Aplicación web desarrollada con Flask para la gestión de un hotel (reservas, clientes, habitaciones, etc.).

---

## Requisitos previos

Antes de comenzar, asegúrate de tener instalado:

- Python 3.x
- Git
- VS Code (opcional)

---

## Clonar el repositorio

```bash
git clone https://github.com/Roroma24/TFE-Hotel.git
cd TFE-Hotel
```

## Configuración del entorno

1. Crear entorno virtual

```
python -m venv venv
```

2. Activar entorno virtual
   Windows:

```
venv\Scripts\activate
```

4. Instalar dependencias

```
pip install -r requirements.txt
```

Ejecutar el proyecto

```
python app.py
```

Abrir en navegador:

```
http://127.0.0.1:5000/
```

## Importante debes de crear tu base de datos con el script sql y generar un .env con lo siguiente

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=hotel_delfino
SECRET_KEY=clave_secreta
```

No olvides modificar tu password.

## Estructura del proyecto

```
TFE-Hotel/
├── static/
├── templates/
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## Reglas del equipo

## 1. Uso de Git

NO trabajar directamente en main
Crear siempre una rama nueva:

```
git checkout -b feature/nombre-funcionalidad
```

Ejemplo:

```
git checkout -b feature/reservas
```

## 2. Flujo de trabajo

Antes de empezar:

```
git pull origin main
```

Después de trabajar:

```
git add .
git commit -m "feat: descripción clara"
git push origin feature/nombre
```

## 3. Tipos de commits

Usar estos prefijos:

feat: nueva funcionalidad

fix: corrección de errores

docs: documentación

refactor: mejora de código

Ejemplo:

```
git commit -m "feat: agregar módulo de reservas"
```

## 4. Buenas prácticas

Usar nombres en inglés para variables y funciones

Mantener código limpio y ordenado

Comentar funciones importantes

Probar antes de subir cambios

No subir código roto

## 5. Entorno virtual

Cada integrante debe crear su propio venv

NO subir la carpeta venv

Usar siempre requirements.txt

## 6. Archivos ignorados

El proyecto incluye .gitignore para evitar subir:

```
venv/
__pycache__/
*.pyc
```

## 7. Trabajo en equipo

No sobrescribir código de otros

Hacer pull antes de empezar

Subir cambios frecuentemente

Mantener comunicación constante
