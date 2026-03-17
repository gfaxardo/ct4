# Backend CT4 — systemd + Nginx (servidor APIS)

Ruta en servidor: **`/root/ct4/backend`** · entorno Python: **`venv`**

---

## 1. Systemd

**Archivo:** `/etc/systemd/system/ct4-backend.service`

```ini
[Unit]
Description=CT4 Backend (FastAPI)
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/ct4/backend
Environment="PATH=/root/ct4/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/root/ct4/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Comandos en el servidor:**

```bash
sudo nano /etc/systemd/system/ct4-backend.service
# Pegar el bloque [Unit]...[Install] de arriba, guardar (Ctrl+O, Enter, Ctrl+X)

sudo systemctl daemon-reload
sudo systemctl enable ct4-backend
sudo systemctl start ct4-backend
sudo systemctl status ct4-backend
```

Ver logs: `sudo journalctl -u ct4-backend -f`

---

## 2. Nginx (API → api-ct4.yego.pro)

**Archivo:** `/etc/nginx/sites-available/ct4-api`

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

**Comandos en el servidor:**

```bash
sudo nano /etc/nginx/sites-available/ct4-api
# Pegar el bloque server { ... }, guardar

sudo ln -sf /etc/nginx/sites-available/ct4-api /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**HTTPS con Certbot:**

```bash
sudo certbot --nginx -d api-ct4.yego.pro
```

---

## Resumen rápido

| Qué              | Dónde / Comando |
|------------------|------------------|
| Servicio         | `/etc/systemd/system/ct4-backend.service` |
| Sitio Nginx      | `/etc/nginx/sites-available/ct4-api` |
| Backend escucha  | `127.0.0.1:8000` |
| Dominio          | `api-ct4.yego.pro` |
| Venv             | `/root/ct4/backend/venv` |
