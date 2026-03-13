# Déploiement VPS Production - UNIGOM Biométrie

## 🚀 Configuration VPS

### Serveur : `95.216.18.174`
- **Backend API** : Port `8000`
- **EHOME Server** : Port `7660`
- **Frontend** : Port `3000`
- **OS** : Ubuntu/Debian (recommandé)

## 📦 Étapes de déploiement sur VPS

### 1. Prérequis sur le VPS
```bash
# Mise à jour système
sudo apt update && sudo apt upgrade -y

# Installer Python et dépendances
sudo apt install python3 python3-pip python3-venv nginx supervisor -y

# Installer Node.js pour le frontend
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y
```

### 2. Configuration Backend

```bash
# Créer dossier application
sudo mkdir -p /var/www/unigom
sudo chown $USER:$USER /var/www/unigom
cd /var/www/unigom

# Cloner ou copier le backend
git clone [votre-repo] backend
cd backend

# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt

# Configurer variables d'environnement
cp .env.example .env
# Éditer .env avec vos valeurs de production
```

### 3. Variables d'environnement (.env)
```bash
# Database
DATABASE_URL=postgresql://postgres.abjlfxnvepxfazsagxtu:mGwH1hb9IeAJ1KO2193LACV6lQFwcpMoKfM996KFBJA@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
DATABASE_PROD_URL=mysql+pymysql://rhunigom_sgad_unigom:PASSWORD@localhost:3306/rhunigom__database_production?charset=utf8mb4
DATABASE_PRESENCE_URL=mysql+pymysql://rhunigom_presence_users:PASSWORD@localhost:3306/rhunigom_presence?charset=utf8mb4

# Sécurité - GÉNÉREZ UN NOUVEAU SECRET !
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# CORS - Ajouter votre domaine
CORS_ORIGINS=http://95.216.18.174:3000,http://localhost:3000

# Environment
ENVIRONMENT=production
DEBUG=False

# EHOME Production
EHOME_PORT=7660
EHOME_SERVER_IP=95.216.18.174
EHOME_DEVICE_ACCOUNT=Unigom
EHOME_KEY=Unigom2026

# Autres
TIMEZONE=Africa/Lubumbashi
CAMPUS_ID=GOMA
DEVICE_ID=HIK001
```

### 4. Configuration Systemd (Backend)
```bash
# Créer service systemd
sudo nano /etc/systemd/system/unigom-backend.service
```

```ini
[Unit]
Description=UNIGOM Backend API
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/unigom/backend
Environment=PATH=/var/www/unigom/backend/venv/bin
ExecStart=/var/www/unigom/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable unigom-backend
sudo systemctl start unigom-backend
sudo systemctl status unigom-backend
```

### 5. Configuration Frontend

```bash
cd /var/www/unigom
# Copier le frontend
git clone [votre-repo] frontend
cd frontend

# Installer dépendances
npm install

# Build pour production
npm run build:prod
```

### 6. Configuration NGINX
```bash
sudo nano /etc/nginx/sites-available/unigom
```

```nginx
server {
    listen 80;
    server_name 95.216.18.174;

    # Frontend
    location / {
        root /var/www/unigom/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /api/v1/ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/unigom /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Configuration Firewall
```bash
# Ouvrir les ports nécessaires
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS (si vous ajoutez SSL)
sudo ufw allow 7660  # EHOME (terminaux)
sudo ufw enable
```

## 🔧 Vérifications

### 1. Backend API
```bash
curl http://95.216.18.174:8000/health
```

### 2. Frontend
```bash
curl http://95.216.18.174/
```

### 3. EHOME Port
```bash
telnet 95.216.18.174 7660
```

### 4. Logs
```bash
# Backend logs
sudo journalctl -u unigom-backend -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 📱 Accès depuis l'extérieur

- **Frontend** : `http://95.216.18.174`
- **API Backend** : `http://95.216.18.174/api/v1/`
- **WebSocket** : `ws://95.216.18.174/api/v1/ws`
- **EHOME** : `95.216.18.174:7660` (terminaux)

## 🔒 Sécurité recommandée

### 1. SSL/TLS (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d 95.216.18.174
```

### 2. Fail2Ban
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
```

### 3. Backup automatique
```bash
# Script backup à créer dans /etc/cron.daily/
```

## 🚨 Monitoring

### 1. Vérifier les services
```bash
sudo systemctl status unigom-backend nginx
```

### 2. Monitoring ressources
```bash
htop
df -h
free -h
```

### 3. Test terminaux Hikvision
Configurez vos terminaux pour pointer vers :
- **IP** : `95.216.18.174`
- **Port** : `7660`
- **Account** : `Unigom`
- **Key** : `Unigom2026`

## 🔄 Mise à jour

Pour mettre à jour :
```bash
cd /var/www/unigom/backend
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart unigom-backend

cd ../frontend
git pull
npm install
npm run build:prod
```

Votre application UNIGOM est maintenant en production sur votre VPS ! 🚀
