#!/bin/bash
# Deploy do projeto veronica-sistema no VPS
# Executar no servidor: bash deploy_vps.sh

set -e
echo "=== DEPLOY VERONICA SISTEMA ==="

# Instalar dependências do sistema
apt-get update -qq
apt-get install -y python3-pip python3-venv git nginx supervisor curl

# Clonar ou atualizar repositório
if [ -d "/opt/veronica-sistema" ]; then
    echo "-> Atualizando repositório..."
    cd /opt/veronica-sistema
    git pull origin main
else
    echo "-> Clonando repositório..."
    git clone https://github.com/elisson83/veronica-sistema.git /opt/veronica-sistema
    cd /opt/veronica-sistema
fi

# Criar ambiente virtual
python3 -m venv /opt/venv
source /opt/venv/bin/activate

# Instalar dependências de todos os painéis
pip install -q flask flask-sqlalchemy flask-login werkzeug python-dotenv \
    apscheduler requests qrcode[pil] reportlab pillow gunicorn flask-limiter \
    flask-wtf cryptography APScheduler

# Criar .env se não existir
if [ ! -f /opt/veronica-sistema/.env ]; then
    cat > /opt/veronica-sistema/.env << 'ENV'
SECRET_KEY=veronica-vps-prod-2025-change-this
SECRET_KEY_MOTOBOY=motoboy-vps-prod-2025
SECRET_KEY_FROTA=frota-vps-prod-2025
FLASK_ENV=production
ENV
    echo "-> .env criado. EDITE /opt/veronica-sistema/.env com suas chaves API!"
fi

# Criar pastas de instância
mkdir -p /opt/veronica-sistema/painelgest/instance
mkdir -p /opt/veronica-sistema/appmotoboy/instance
mkdir -p /opt/veronica-sistema/painelfrota/instance

# Configurar Nginx
cat > /etc/nginx/sites-available/veronica << 'NGINX'
server {
    listen 80;
    server_name _;

    location /painelgest { proxy_pass http://127.0.0.1:5002; proxy_set_header Host $host; }
    location /motoboy    { proxy_pass http://127.0.0.1:5003; proxy_set_header Host $host; }
    location /frota      { proxy_pass http://127.0.0.1:5004; proxy_set_header Host $host; }
    location /dono       { proxy_pass http://127.0.0.1:5005; proxy_set_header Host $host; }
}

server { listen 5002; location / { proxy_pass http://127.0.0.1:5002; } }
server { listen 5003; location / { proxy_pass http://127.0.0.1:5003; } }
server { listen 5004; location / { proxy_pass http://127.0.0.1:5004; } }
server { listen 5005; location / { proxy_pass http://127.0.0.1:5005; } }
NGINX
ln -sf /etc/nginx/sites-available/veronica /etc/nginx/sites-enabled/veronica
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Parar serviços anteriores
pkill -f "painelgest/app.py" 2>/dev/null || true
pkill -f "appmotoboy/app.py" 2>/dev/null || true
pkill -f "painelfrota/app.py" 2>/dev/null || true
pkill -f "run_dono_5005.py" 2>/dev/null || true
sleep 2

# Subir todos os serviços com nohup
cd /opt/veronica-sistema
source /opt/venv/bin/activate

nohup python painelgest/app.py > /var/log/painelgest.log 2>&1 &
echo "PainelGest PID: $!"

nohup python appmotoboy/app.py > /var/log/appmotoboy.log 2>&1 &
echo "AppMotoboy PID: $!"

nohup python painelfrota/app.py > /var/log/painelfrota.log 2>&1 &
echo "PainelFrota PID: $!"

nohup python run_dono_5005.py > /var/log/painel_dono.log 2>&1 &
echo "PainelDono PID: $!"

sleep 5

# Verificar serviços
echo ""
echo "=== STATUS DOS SERVICOS ==="
for port in 5002 5003 5004 5005; do
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/login 2>/dev/null | grep -qE "^[23]"; then
        echo "  :$port — OK"
    else
        echo "  :$port — FALHOU (verifique: tail -50 /var/log/painel*.log)"
    fi
done

IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "=== LINKS DE ACESSO ==="
echo "  Super Admin:        http://$IP:5002/super/login"
echo "  PainelGest:         http://$IP:5002/login"
echo "  PainelRestaurante:  http://$IP:5002/restaurante/login"
echo "  Painel do Dono:     http://$IP:5002/dono/login"
echo "  AppMotoboy:         http://$IP:5003/login"
echo "  PainelFrota:        http://$IP:5004/login"
echo ""
echo "=== DEPLOY CONCLUIDO ==="
