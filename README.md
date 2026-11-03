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

- **Orígenes** (solo administradores): lista de orígenes de las cartas. Hay que crear al menos uno antes de subir documentos. Un origen con documentos o sucursales no se puede borrar. La API acepta `parent_id` para registrar sucursales más adelante.
- **Subir**: carta responsiva en PDF de hasta `MAX_UPLOAD_MB` MB (50 por defecto; el mismo valor limita nginx). Se capturan el origen, el nombre completo del propietario (nombre y al menos un apellido) y, opcionalmente, la fecha del documento. El tipo es siempre "Carta responsiva" y el título se toma del nombre del archivo. Si el propietario ya existe con otra escritura ("José Pérez" y "jose perez"), se reutiliza. Un PDF idéntico (mismo SHA-256) no se guarda dos veces: la app enlaza al documento existente.
- **Documentos**: filtros por propietario (sin acentos ni mayúsculas), origen (incluye sucursales) y rango de fechas. El detalle permite cambiar origen, propietario y fecha, y muestra el PDF. Solo quien lo subió o un administrador puede editarlo.

Al elegir un PDF en **Subir**, el servidor lee las dos primeras páginas (capa de texto o, si es un escaneo, OCR con Tesseract en español) y sugiere la fecha del recuadro "Fecha:" y el nombre impreso sobre la línea del área ("Seguridad"). Las sugerencias solo llenan campos que el usuario no ha tocado y siempre se pueden corregir; si no se encuentra nada, los campos quedan vacíos. Al guardar se registra lo sugerido y si el usuario lo cambió (`owner_name_edited`, `document_date_edited`). La imagen de Docker incluye Tesseract; sin Docker hace falta instalarlo y, si no está en el `PATH`, indicar la ruta en `TESSERACT_CMD`. Sin Tesseract la carga funciona igual, solo sin sugerencias en escaneos.

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

## Producción en red local

`docker-compose.prod.yml` agrega Caddy delante de `web` con HTTPS y un certificado de su autoridad interna (`tls internal`). Caddy publica solo el 443 en la IP del servidor, así que se entra siempre con `https://`. El 80 no se publica porque en el servidor puede estar ocupado por otros servicios, como IIS. `web` deja de publicar el 8080.

1. Copiar la configuración (`cp .env.example .env`) y, en `.env`:

   ```sh
   DOCVAULT_HOST=192.168.1.50      # IP del servidor en la red local
   SESSION_COOKIE_SECURE=true
   ```

2. Levantar:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

   El certificado y la autoridad interna se guardan en los volúmenes `caddy_data` y `caddy_config`, así que sobreviven a reinicios y reconstrucciones. No los borres con `down -v`: cambiaría la autoridad y habría que volver a instalarla en cada PC.

3. Crear el primer administrador (pide la contraseña dos veces):

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm api python -m app.cli create-admin --username admin --full-name "Nombre Apellido"
   ```

4. Exportar el certificado raíz de Caddy:

   ```sh
   docker compose -f docker-compose.yml -f docker-compose.prod.yml cp caddy:/data/caddy/pki/authorities/local/root.crt ./caddy-root.crt
   ```

5. Instalarlo en cada PC con Windows que use docvault, en "Entidades de certificación raíz de confianza" del equipo:
   - Doble clic en `caddy-root.crt` > Instalar certificado > Equipo local > Colocar todos los certificados en el siguiente almacén > Entidades de certificación raíz de confianza.
   - O en PowerShell como administrador:

     ```powershell
     Import-Certificate -FilePath .\caddy-root.crt -CertStoreLocation Cert:\LocalMachine\Root
     ```

   Después abrir `https://<DOCVAULT_HOST>`. Chrome y Edge usan ese almacén; reinicia el navegador si ya estaba abierto.

6. En el servidor, abrir 443 solo en el perfil Privado del firewall de Windows (PowerShell como administrador):

   ```powershell
   New-NetFirewallRule -DisplayName "docvault HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -Profile Private
   ```

   La red del servidor debe estar marcada como Privada en Configuración > Red e Internet.

Para volver al entorno de desarrollo, quitar Caddy con `docker compose -f docker-compose.yml -f docker-compose.prod.yml rm -sf caddy` y después correr `docker compose up -d`.

## Respaldo

Todo el estado está en `./storage`.

- Con la app detenida: `docker compose stop api`, copiar `storage/docvault.db` (y la carpeta `storage` completa cuando haya PDFs), y después `docker compose start api`.
- En caliente, con `sqlite3`:

  ```sh
  sqlite3 storage/docvault.db ".backup 'docvault-backup.db'"
  ```

No copiar solo `docvault.db` con la app en marcha: en modo WAL hay cambios recientes en `docvault.db-wal`.
