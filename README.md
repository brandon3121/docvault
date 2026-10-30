# docvault

Aplicación interna para guardar PDFs con destino, tipo, propietario y fecha, con inicio de sesión por usuario.

- Backend: FastAPI + SQLAlchemy 2 + Alembic sobre SQLite (WAL).
- Frontend: React + TypeScript (Vite), servido por nginx.
- Datos: todo vive en `./storage`: la base de datos `docvault.db` y los PDFs en `storage/documents/ab/cd/<sha256>.pdf`.

## Puesta en marcha con Docker

1. Copiar la configuración:

   ```sh
   cp .env.example .env
   ```

2. Construir y levantar:

   ```sh
   docker compose up --build -d
   ```

   El servicio `api` aplica las migraciones de Alembic al arrancar.

3. Crear el primer administrador (pide la contraseña dos veces):

   ```sh
   docker compose run --rm api python -m app.cli create-admin --username admin --full-name "Nombre Apellido"
   ```

4. Abrir http://localhost:8080

Comprobación rápida:

```sh
curl http://localhost:8080/api/health
```

## Uso

- **Catálogos** (solo administradores): destinos jerárquicos, tipos de documento y propietarios. Hay que crear al menos un destino y un tipo antes de subir documentos. Un catálogo con documentos asociados no se puede borrar.
- **Subir**: PDF de hasta `MAX_UPLOAD_MB` MB (50 por defecto; el mismo valor limita nginx). Un PDF idéntico (mismo SHA-256) no se guarda dos veces: la app enlaza al documento existente. Si el propietario escrito no existe, se crea.
- **Documentos**: búsqueda por texto en el título (FTS5), filtros por propietario (sin acentos ni mayúsculas), destino (incluye subdestinos), tipo y rango de fechas. El detalle permite editar metadatos y muestra el PDF. Solo quien lo subió o un administrador puede editarlo.

La extracción automática de texto, propietario y fecha todavía no existe: esos datos se capturan a mano.

## Desarrollo local sin Docker

Backend (desde `backend/`):

```sh
python -m venv .venv
.venv/Scripts/activate        # Windows; en Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///../storage/docvault.db   # PowerShell: $env:DATABASE_URL="sqlite:///../storage/docvault.db"
alembic upgrade head
python -m app.cli create-admin --username admin --full-name "Nombre Apellido"
uvicorn app.main:app --reload --port 8000
```

Pruebas:

```sh
pytest
```

Frontend (desde `frontend/`, con el backend en el puerto 8000):

```sh
npm install
npm run dev
```

Vite envía `/api` a `http://localhost:8000`.

## Despliegue en servidor

Los mismos pasos que arriba (`cp .env.example .env`, `docker compose up --build -d`, `create-admin`), con estos cambios:

- En `.env`, poner `SESSION_COOKIE_SECURE=true`. La cookie de sesión solo viajará por HTTPS.
- Poner HTTPS delante del puerto 8080, por ejemplo con Caddy en el host:

  ```
  docvault.ejemplo.com {
      reverse_proxy localhost:8080
  }
  ```

  O con nginx en el host, con un certificado y `proxy_pass http://127.0.0.1:8080;`.
- Si el proxy está en el mismo host, conviene publicar solo en loopback: `WEB_PORT=127.0.0.1:8080`.

## Respaldo

Todo el estado está en `./storage`.

- Con la app detenida: `docker compose stop api`, copiar `storage/docvault.db` (y la carpeta `storage` completa cuando haya PDFs), y después `docker compose start api`.
- En caliente, con `sqlite3`:

  ```sh
  sqlite3 storage/docvault.db ".backup 'docvault-backup.db'"
  ```

No copiar solo `docvault.db` con la app en marcha: en modo WAL hay cambios recientes en `docvault.db-wal`.
