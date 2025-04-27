# tabula-backend

## Español

Backend del sistema **Tábula**, una aplicación de gestión de inventario con control en tiempo real, desarrollado con [FastAPI](https://fastapi.tiangolo.com/) y PostgreSQL.

Este repositorio contiene la API RESTful, la lógica de autenticación, la gestión de stock, y soporte para WebSockets.

---

## Navegación

- [Repositorio principal](https://github.com/duquediazn/tabula)
- [Backend (FastAPI + PostgreSQL)](https://github.com/duquediazn/tabula-backend)
- [Frontend (React + Tailwind)](https://github.com/duquediazn/tabula-frontend)

---

## Tecnologías principales

- [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/) + [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- Autenticación JWT (access y refresh tokens)
- [WebSocket](https://developer.mozilla.org/es/docs/Web/API/WebSockets_API) para notificaciones en tiempo real

---

## Instalación local

1. Clona el repositorio:

```bash
git clone https://github.com/duquediazn/tabula-backend.git
cd tabula-backend

```

2. Crea un entorno virtual e instálalo todo:

```
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Crea un archivo .env basado en el archivo de ejemplo:

```
cp .env.template .env
```

4. Inicia la base de datos local (por ejemplo, PostgreSQL en localhost:5432) y actualiza la variable DATABASE_URL en .env.

5. Ejecuta la API

```
uvicorn app.main:app --reload
```

---

## Variables de entorno (.env)

```
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/tabula-db
SECRET_KEY=clave_super_secreta
ACCESS_TOKEN_DURATION=60
REFRESH_TOKEN_DURATION=7
```

---

## API y documentación interactiva

Este backend está desarrollado con [FastAPI](https://fastapi.tiangolo.com/), lo que permite generar automáticamente una documentación interactiva accesible desde el navegador.

---

### Documentación Swagger (OpenAPI)

Una vez corras la API localmente, puedes acceder a la documentación desde:

- [http://localhost:8000/docs](http://localhost:8000/docs) → Interfaz Swagger (explorable y testeable)
- [http://localhost:8000/redoc](http://localhost:8000/redoc) → Redoc (alternativa más estructurada)

Cuando el backend esté desplegado, estos mismos endpoints estarán disponibles bajo la URL pública del servidor, por ejemplo:

- `https://<tu-app>.onrender.com/docs`

Desde estas interfaces puedes consultar, probar y entender todos los endpoints disponibles en tiempo real.

---

## Licencia

Este proyecto está licenciado bajo los términos de la GNU General Public License v3.0.

Consulta el archivo LICENSE para más detalles.

---

> Este repositorio está basado en una versión previa desarrollada localmente, reorganizada y limpiada para su publicación pública.

---

## English

Backend of the **Tábula** system, an inventory management application with real-time control, developed using [FastAPI](https://fastapi.tiangolo.com/) and PostgreSQL.

This repository contains the RESTful API, authentication logic, stock management, and WebSocket support.

---

## Navigation

- [Main repository (Documentation)](https://github.com/duquediazn/tabula)
- [Backend (FastAPI + PostgreSQL)](https://github.com/duquediazn/tabula-backend)
- [Frontend (React + Tailwind)](https://github.com/duquediazn/tabula-frontend)

---

## Main Technologies

- [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- [PostgreSQL](https://www.postgresql.org/)
- [SQLModel](https://sqlmodel.tiangolo.com/) + [SQLAlchemy](https://www.sqlalchemy.org/) (ORM)
- JWT Authentication (access and refresh tokens)
- [WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API) for real-time notifications

---

## Local Installation

1. Clone the repository:

```bash
git clone https://github.com/duquediazn/tabula-backend.git
cd tabula-backend
```

2. Create a virtual environment and install dependencies:

```
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Create a .env file based on the example:

```
cp .env.template .env
```

4. Start your local PostgreSQL database (e.g., on localhost:5432) and update the DATABASE_URL value in .env.

5. Run the API:

```
uvicorn app.main:app --reload
```

---

## Environment Variables (.env)

```
DATABASE_URL=postgresql://user:password@localhost:5432/tabula-db
SECRET_KEY=your_super_secret_key
ACCESS_TOKEN_DURATION=60
REFRESH_TOKEN_DURATION=7
```

---

## API & Interactive Documentation

This backend is built with FastAPI, which automatically generates interactive documentation accessible via your browser.

---

### Swagger (OpenAPI) Documentation

Once the API is running locally, you can access the docs at:

- [http://localhost:8000/docs](http://localhost:8000/docs) → Swagger UI (interactive and testable)
- [http://localhost:8000/redoc](http://localhost:8000/redoc) → Redoc (more structured view)

When deployed, these endpoints will be available under the public server URL, for example:

- `https://<tu-app>.onrender.com/docs`

These interfaces allow you to explore, test, and understand the available endpoints in real time.

---

## License

This project is licensed under the terms of the GNU General Public License v3.0.

See the LICENSE file for more details.

---

> This repository is based on a previous local development version, cleaned and restructured for public release.
