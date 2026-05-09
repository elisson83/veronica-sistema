#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Script de instalação do Nginx + Certbot para o Ecossistema Verônica
# Servidor: 177.7.50.92
# Uso: bash instalar_nginx.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -e

DEPLOY_DIR="/home/ubuntu/veronica"
CONF_NAME="veronica"

echo "=== Instalando Nginx e Certbot ==="
sudo apt update -qq
sudo apt install -y nginx certbot python3-certbot-nginx

echo "=== Copiando configuração ==="
sudo cp veronica.conf /etc/nginx/sites-available/${CONF_NAME}
sudo ln -sf /etc/nginx/sites-available/${CONF_NAME} /etc/nginx/sites-enabled/${CONF_NAME}
sudo rm -f /etc/nginx/sites-enabled/default

echo "=== Testando configuração ==="
sudo nginx -t

echo "=== Iniciando Nginx ==="
sudo systemctl enable nginx
sudo systemctl restart nginx

echo ""
echo "=== ATENÇÃO: Configure os certificados SSL ==="
echo "Execute para cada domínio:"
echo "  sudo certbot --nginx -d motoboy.SEU_DOMINIO.com"
echo "  sudo certbot --nginx -d frota.SEU_DOMINIO.com"
echo "  sudo certbot --nginx -d gest.SEU_DOMINIO.com"
echo "  sudo certbot --nginx -d restaurante.SEU_DOMINIO.com"
echo ""
echo "Ou use nip.io (sem DNS próprio):"
echo "  sudo certbot --nginx -d motoboy.177.7.50.92.nip.io"
echo "  sudo certbot --nginx -d frota.177.7.50.92.nip.io"
echo "  sudo certbot --nginx -d gest.177.7.50.92.nip.io"
echo "  sudo certbot --nginx -d restaurante.177.7.50.92.nip.io"
echo ""
echo "=== Nginx instalado com sucesso ==="
