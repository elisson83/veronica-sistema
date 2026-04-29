import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def _cfg():
    return (
        os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
        int(os.environ.get('SMTP_PORT', 587)),
        os.environ.get('SMTP_USER', os.environ.get('GMAIL_USER', '')),
        os.environ.get('SMTP_PASS', os.environ.get('GMAIL_PASSWORD', '')),
    )


def enviar_email(para, assunto, corpo, pdf_bytes=None, nome_pdf='comprovante.pdf'):
    """Envia e-mail via Gmail SMTP. Retorna (True, None) ou (False, mensagem_erro)."""
    host, porta, usuario, senha = _cfg()
    if not usuario:
        return False, 'SMTP não configurado (SMTP_USER ausente no .env)'
    try:
        msg = MIMEMultipart()
        msg['From']    = usuario
        msg['To']      = para
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo, 'plain', 'utf-8'))
        if pdf_bytes:
            parte = MIMEBase('application', 'octet-stream')
            parte.set_payload(pdf_bytes)
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f'attachment; filename="{nome_pdf}"')
            msg.attach(parte)
        with smtplib.SMTP(host, porta) as s:
            s.starttls()
            s.login(usuario, senha)
            s.sendmail(usuario, para, msg.as_string())
        return True, None
    except Exception as e:
        return False, str(e)


def enviar_reset_senha(para, link, nome_painel='Sistema', nome_usuario=''):
    saudacao = f'Olá{", " + nome_usuario if nome_usuario else ""}!'
    corpo = (
        f'{saudacao}\n\n'
        f'Você solicitou a redefinição de senha no {nome_painel}.\n\n'
        f'Clique no link abaixo para criar uma nova senha:\n{link}\n\n'
        f'O link expira em 2 horas.\n\n'
        f'Se não foi você, ignore este e-mail.\n\n'
        f'— {nome_painel}'
    )
    return enviar_email(para, f'Redefinir senha — {nome_painel}', corpo)


def enviar_comprovante_pdf(para, pdf_bytes, periodo, nome_arquivo='comprovante.pdf'):
    corpo = (
        f'Olá!\n\n'
        f'Segue em anexo o comprovante financeiro referente ao período: {periodo}.\n\n'
        f'Gerado automaticamente em {datetime.now().strftime("%d/%m/%Y às %H:%M")}.\n\n'
        f'— Sistema Verônica IA'
    )
    return enviar_email(para, f'Comprovante Financeiro — {periodo}', corpo,
                        pdf_bytes=pdf_bytes, nome_pdf=nome_arquivo)


def notificacao_sistema(para, titulo, mensagem):
    corpo = (
        f'[NOTIFICAÇÃO — Verônica IA]\n\n'
        f'{mensagem}\n\n'
        f'Enviado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}'
    )
    return enviar_email(para, f'[Verônica] {titulo}', corpo)
