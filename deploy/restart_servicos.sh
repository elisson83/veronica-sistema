#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# Reinicia todos os serviços do Ecossistema Verônica no servidor
# Servidor: 177.7.50.92
# Uso: bash restart_servicos.sh
# ═══════════════════════════════════════════════════════════════════════════════
set -e

DEPLOY_DIR="/home/ubuntu/veronica"
VENV="$DEPLOY_DIR/venv/bin/activate"

echo "=== Parando serviços existentes ==="
pkill -f "appmotoboy/app.py"     2>/dev/null || true
pkill -f "painelfrota/app.py"    2>/dev/null || true
pkill -f "painelgest/app.py"     2>/dev/null || true
pkill -f "painelrestaurante/app.py" 2>/dev/null || true
sleep 2

echo "=== Atualizando código ==="
cd "$DEPLOY_DIR"
git pull origin main

echo "=== Instalando dependências ==="
source "$VENV"
pip install -q -r appmotoboy/requirements.txt    2>/dev/null || true
pip install -q -r painelfrota/requirements.txt   2>/dev/null || true
pip install -q -r painelgest/requirements.txt    2>/dev/null || true
pip install -q -r painelrestaurante/requirements.txt 2>/dev/null || true

echo "=== Iniciando serviços ==="
nohup python appmotoboy/app.py    > logs/appmotoboy.log    2>&1 &
nohup python painelfrota/app.py   > logs/painelfrota.log   2>&1 &
nohup python painelgest/app.py    > logs/painelgest.log    2>&1 &
nohup python painelrestaurante/app.py > logs/painelrestaurante.log 2>&1 &

sleep 3
echo ""
echo "=== Status dos serviços ==="
for port in 5002 5003 5004 5006; do
    if curl -s --max-time 2 "http://localhost:$port" > /dev/null 2>&1; then
        echo "  [OK] Porta $port respondendo"
    else
        echo "  [AV] Porta $port nao respondeu (pode estar inicializando)"
    fi
done

echo ""
echo "=== Recarregando Nginx ==="
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "=== Deploy concluido ==="
echo "    Logs em: $DEPLOY_DIR/logs/"
