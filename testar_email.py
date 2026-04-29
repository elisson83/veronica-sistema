"""
Script de teste do sistema de e-mail via Gmail SMTP.
Uso: python testar_email.py [email_destino]
     Se não passar destino, envia para o próprio SMTP_USER.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.email_utils import enviar_email, enviar_reset_senha, notificacao_sistema

usuario = os.environ.get('SMTP_USER', '')
print(f'\n=== Teste de E-mail — Verônica IA ===')
print(f'SMTP_HOST : {os.environ.get("SMTP_HOST", "smtp.gmail.com")}')
print(f'SMTP_PORT : {os.environ.get("SMTP_PORT", "587")}')
print(f'SMTP_USER : {usuario}')
print(f'SMTP_PASS : {"*" * len(os.environ.get("SMTP_PASS", "")) or "(vazio)"}')

destino = sys.argv[1] if len(sys.argv) > 1 else usuario
if not destino:
    print('\n[ERRO] SMTP_USER não definido no .env. Verifique o arquivo.')
    sys.exit(1)

print(f'\nEnviando e-mail de teste para: {destino}')

ok, erro = enviar_email(
    destino,
    '✅ Teste de E-mail — Verônica IA',
    'Este é um e-mail de teste enviado pelo sistema Verônica IA.\n\n'
    'Se você recebeu esta mensagem, o Gmail SMTP está funcionando corretamente!\n\n'
    'Funcionalidades ativas:\n'
    '  • Reset de senha (todos os painéis)\n'
    '  • Comprovantes PDF para o contador\n'
    '  • Notificações automáticas do sistema\n\n'
    '— Verônica IA'
)

if ok:
    print(f'[OK] E-mail enviado com sucesso para {destino}!')
else:
    print(f'[ERRO] Falha ao enviar: {erro}')
    sys.exit(1)

print('\nTestando notificação de sistema...')
ok2, erro2 = notificacao_sistema(
    destino,
    'Sistema iniciado',
    'O sistema Verônica IA foi iniciado e o e-mail está configurado corretamente.'
)
if ok2:
    print('[OK] Notificação de sistema enviada!')
else:
    print(f'[AVISO] Notificação falhou: {erro2}')

print('\n=== Todos os testes concluídos ===')
