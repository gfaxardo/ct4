# Frontend CT4 — build estático + Nginx (sin systemd, servidor APIS)

Build React/Next → copiar a **www** → Nginx sirve los archivos. Sin Node en producción.

Ruta del repo: **`/root/ct4/frontend`** · carpeta web: **`/var/www/ct4-frontend`** · dominio: **ct4.yego.pro**

---

## 1. Build

En el servidor (o en tu máquina y subes la carpeta):

```bash
cd /root/ct4/frontend
npm install
npm run build
```

Eso genera la carpeta **`out`** con HTML, JS y CSS estáticos.

---

## 2. Copiar el build a www

```bash
sudo mkdir -p /var/www/ct4-frontend
sudo cp -r /root/ct4/frontend/out/* /var/www/ct4-frontend/
sudo chown -R www-data:www-data /var/www/ct4-frontend
```

Cada vez que hagas un nuevo build, repite el `cp` (y si quieres el `chown`):

```bash
sudo cp -r /root/ct4/frontend/out/* /var/www/ct4-frontend/
```

---

## 3. Nginx (servir archivos estáticos → ct4.yego.pro)

**Archivo:** `/etc/nginx/sites-available/ct4-frontend`

```nginx
server {
    listen 80;
    server_name ct4.yego.pro;
    root /var/www/ct4-frontend;
    index index.html;
    location / {
        try_files $uri $uri/ $uri.html /index.html;
    }
}
```

**Comandos en el servidor:**

```bash
sudo nano /etc/nginx/sites-available/ct4-frontend
# Pegar el bloque server { ... }, guardar

sudo ln -sf /etc/nginx/sites-available/ct4-frontend /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**HTTPS con Certbot:**

```bash
sudo certbot --nginx -d ct4.yego.pro
```

---

## Resumen rápido

| Paso   | Comando |
|--------|---------|
| Build  | `cd /root/ct4/frontend && npm install && npm run build` |
| Copiar | `sudo cp -r /root/ct4/frontend/out/* /var/www/ct4-frontend/` |
| Nginx  | `root /var/www/ct4-frontend` en el sitio de ct4.yego.pro |

No hace falta tener Node corriendo: Nginx sirve directamente los archivos de `/var/www/ct4-frontend`.
