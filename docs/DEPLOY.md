# Despliegue CT4

## Servidor

- **IP:** `5.161.229.77`

## Dominios

| Servicio  | Dominio            | Descripción                    |
|-----------|--------------------|--------------------------------|
| Backend (API) | **api-ct4.yego.pro** | API (FastAPI / Uvicorn)   |
| Frontend (UI) | **ct4.yego.pro**   | Aplicación web (Next.js)       |

## Configuración por entorno

### Backend (en el servidor)

- Apuntar el dominio **api-ct4.yego.pro** al servidor (DNS / proxy reverso, p. ej. Nginx).
- En el `.env` del backend puedes usar **DATABASE_URL** o las variables separadas (igual que en local):

**Opción 1 — URL completa**
```env
ENVIRONMENT=production
CORS_ORIGINS=https://ct4.yego.pro
DATABASE_URL=postgresql://usuario:contraseña@host:5432/nombre_bd
```

**Opción 2 — Variables separadas (recomendado, igual que en local)**
```env
DB_HOST=168.119.226.236
DB_PORT=5432
DB_NAME=yego_integral
DB_USER=yego_user
DB_PASSWORD=tu_contraseña
ENVIRONMENT=production
CORS_ORIGINS=https://ct4.yego.pro
```

- `CORS_ORIGINS` debe incluir el origen del frontend (`https://ct4.yego.pro`) para que el navegador permita las peticiones desde la UI al API.

### Frontend (build / servidor)

- Apuntar el dominio **ct4.yego.pro** al servidor (o al mismo host con distinto virtualhost).
- En build o en el entorno del frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://api-ct4.yego.pro
```

- Así la aplicación web (ct4.yego.pro) llamará al backend en **https://api-ct4.yego.pro**.

## Cómo correr el backend en el servidor

### 1. Conectar y clonar/actualizar el repo

```bash
ssh tu_usuario@5.161.229.77
cd /ruta/donde/esté/el/proyecto   # ej. /home/tu_usuario/ct4
git pull   # si ya está clonado
```

### 2. Backend: venv y dependencias

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Configurar .env en el servidor

Copia la plantilla y rellena (al menos `DB_PASSWORD`):

```bash
cp .env.production.example .env
nano .env   # o vim: poner DB_PASSWORD y revisar el resto
```

### 4. Probar que arranca

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Si ves "Uvicorn running on http://0.0.0.0:8000", está bien. Ctrl+C para parar.

### 5. Dejarlo corriendo con systemd (recomendado)

Así el backend se inicia solo al arrancar el servidor y se reinicia si se cae.

```bash
# En el servidor, edita el .service con tus rutas y usuario
sudo nano /etc/systemd/system/ct4-backend.service
```

Contenido de ejemplo (cambia `tu_usuario` y las rutas):

```ini
[Unit]
Description=CT4 Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=tu_usuario
Group=tu_usuario
WorkingDirectory=/home/tu_usuario/ct4/backend
Environment="PATH=/home/tu_usuario/ct4/backend/.venv/bin:/usr/bin:/bin"
ExecStart=/home/tu_usuario/ct4/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Activar y arrancar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ct4-backend
sudo systemctl start ct4-backend
sudo systemctl status ct4-backend
```

Ver logs: `sudo journalctl -u ct4-backend -f`

### 6. Nginx como proxy (backend + frontend y HTTPS)

Sí es necesario configurar Nginx para ambos dominios: así Nginx recibe la petición, hace de proxy al backend o al frontend y Certbot puede poner HTTPS.

**Backend / API (api-ct4.yego.pro)** — archivo ej. `/etc/nginx/sites-available/ct4-api`:

```nginx
server {
    listen 80;
    server_name api-ct4.yego.pro;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Frontend / UI (ct4.yego.pro)** — archivo ej. `/etc/nginx/sites-available/ct4-frontend`:

El frontend en producción se ejecuta con `next start` (puerto 3000). Nginx hace proxy a ese proceso:

```nginx
server {
    listen 80;
    server_name ct4.yego.pro;
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Activar sitios y recargar Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/ct4-api /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/ct4-frontend /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Certificados HTTPS (Let's Encrypt) para los dos dominios:

```bash
sudo certbot --nginx -d ct4.yego.pro -d api-ct4.yego.pro
```

(O por separado: `sudo certbot --nginx -d ct4.yego.pro` y `sudo certbot --nginx -d api-ct4.yego.pro`.)

---

## Resumen

- **Servidor:** `5.161.229.77`
- **Backend (API):** `https://api-ct4.yego.pro`
- **Frontend (UI):** `https://ct4.yego.pro`
