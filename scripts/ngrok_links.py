"""
Agrega os links publicos de todos os tuneis ngrok ativos (portas 4040-4043)
e abre uma pagina HTML no navegador com todos os links.
"""
import json
import os
import sys
import webbrowser
import tempfile
from urllib import request
from datetime import datetime

PAINEIS = {
    4040: {'porta': 5002, 'nome': 'PainelGest',   'cor': '#f59e0b', 'icone': '&#9881;'},
    4041: {'porta': 5003, 'nome': 'AppMotoboy',   'cor': '#3b82f6', 'icone': '&#128690;'},
    4042: {'porta': 5004, 'nome': 'PainelFrota',  'cor': '#10b981', 'icone': '&#128666;'},
    4043: {'porta': 5005, 'nome': 'PainelDono',   'cor': '#8b5cf6', 'icone': '&#128081;'},
}


def buscar_tuneis(api_porta):
    try:
        url = f'http://127.0.0.1:{api_porta}/api/tunnels'
        with request.urlopen(url, timeout=3) as r:
            dados = json.loads(r.read())
            return dados.get('tunnels', [])
    except Exception:
        return []


def url_https(tuneis):
    for t in tuneis:
        u = t.get('public_url', '')
        if u.startswith('https://'):
            return u
    return None


resultados = []
for api_porta, info in PAINEIS.items():
    tuneis = buscar_tuneis(api_porta)
    url = url_https(tuneis)
    resultados.append({
        'nome':  info['nome'],
        'porta': info['porta'],
        'cor':   info['cor'],
        'icone': info['icone'],
        'url':   url,
        'ok':    url is not None,
    })

# ── Saída no terminal ─────────────────────────────────────────────────────────
print('\n=== NGROK LINKS — Veronica IA ===\n')
for r in resultados:
    status = 'OK' if r['ok'] else 'SEM TUNEL'
    print(f"  {r['nome']:<14} (:{r['porta']})  {status}")
    if r['ok']:
        print(f"  {r['url']}\n")
    else:
        print()

# ── Gera HTML ────────────────────────────────────────────────────────────────
agora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
ativos = sum(1 for r in resultados if r['ok'])

cards_html = ''
for r in resultados:
    if r['ok']:
        cards_html += f"""
    <div class="card" style="border-left: 4px solid {r['cor']}">
      <div class="card-header">
        <span class="icone" style="color:{r['cor']}">{r['icone']}</span>
        <span class="nome">{r['nome']}</span>
        <span class="porta">:{r['porta']}</span>
        <span class="badge ok">ONLINE</span>
      </div>
      <div class="url-row">
        <a href="{r['url']}" target="_blank" id="url-{r['porta']}">{r['url']}</a>
        <button onclick="copiar('{r['url']}', this)" class="btn-copy">Copiar</button>
        <a href="{r['url']}" target="_blank" class="btn-abrir">Abrir</a>
      </div>
    </div>"""
    else:
        cards_html += f"""
    <div class="card offline" style="border-left: 4px solid #4b5563">
      <div class="card-header">
        <span class="icone" style="color:#4b5563">{r['icone']}</span>
        <span class="nome" style="color:#6b7280">{r['nome']}</span>
        <span class="porta" style="color:#4b5563">:{r['porta']}</span>
        <span class="badge off">OFFLINE</span>
      </div>
      <div class="url-row" style="color:#4b5563">Tunel nao encontrado na porta {r['porta'] - 5002 + 4040}</div>
    </div>"""

html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="15">
<title>Ngrok Links — Veronica IA</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 32px; }}
  h1 {{ font-size: 26px; color: #facc15; margin-bottom: 4px; }}
  .sub {{ color: #64748b; font-size: 13px; margin-bottom: 28px; }}
  .resumo {{ display:flex; gap: 20px; margin-bottom: 28px; }}
  .stat {{ background: #1e293b; border-radius: 10px; padding: 14px 24px; text-align: center; }}
  .stat .n {{ font-size: 28px; font-weight: bold; color: #facc15; }}
  .stat .l {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 18px 22px; margin-bottom: 16px; }}
  .card.offline {{ opacity: 0.5; }}
  .card-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }}
  .icone {{ font-size: 22px; }}
  .nome {{ font-size: 17px; font-weight: 600; }}
  .porta {{ font-size: 12px; color: #64748b; background: #0f172a; padding: 2px 8px; border-radius: 6px; }}
  .badge {{ font-size: 11px; padding: 3px 9px; border-radius: 20px; font-weight: bold; margin-left: auto; }}
  .badge.ok {{ background: #065f46; color: #6ee7b7; }}
  .badge.off {{ background: #1f2937; color: #4b5563; }}
  .url-row {{ display: flex; align-items: center; gap: 10px; }}
  .url-row a {{ color: #34d399; text-decoration: none; font-size: 15px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }}
  .url-row a:hover {{ text-decoration: underline; }}
  .btn-copy {{ background: #1d4ed8; border: none; color: #fff; padding: 7px 16px; border-radius: 7px; cursor: pointer; font-size: 13px; white-space: nowrap; }}
  .btn-copy:hover {{ background: #2563eb; }}
  .btn-copy.copiado {{ background: #065f46; }}
  .btn-abrir {{ background: #0f172a; border: 1px solid #334155; color: #94a3b8; padding: 7px 14px; border-radius: 7px; cursor: pointer; font-size: 13px; text-decoration: none; white-space: nowrap; }}
  .btn-abrir:hover {{ background: #1e293b; color: #e2e8f0; }}
  .footer {{ margin-top: 24px; font-size: 12px; color: #334155; text-align: center; }}
  .ngrok-dash {{ display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap; }}
  .ngrok-dash a {{ background: #1e293b; color: #64748b; padding: 7px 14px; border-radius: 7px; text-decoration: none; font-size: 12px; border: 1px solid #334155; }}
  .ngrok-dash a:hover {{ color: #e2e8f0; }}
</style>
</head>
<body>
  <h1>&#127760; Ngrok Links — Veronica IA</h1>
  <div class="sub">Atualizado em {agora} &nbsp;|&nbsp; Atualiza automaticamente a cada 15s</div>

  <div class="resumo">
    <div class="stat"><div class="n">{ativos}</div><div class="l">Tuneis ativos</div></div>
    <div class="stat"><div class="n">{len(resultados) - ativos}</div><div class="l">Offline</div></div>
    <div class="stat"><div class="n">{len(resultados)}</div><div class="l">Total</div></div>
  </div>

  {cards_html}

  <div class="ngrok-dash">
    <span style="color:#475569;font-size:12px;align-self:center">Dashboards ngrok:</span>
    <a href="http://127.0.0.1:4040" target="_blank">4040 - PainelGest</a>
    <a href="http://127.0.0.1:4041" target="_blank">4041 - AppMotoboy</a>
    <a href="http://127.0.0.1:4042" target="_blank">4042 - PainelFrota</a>
    <a href="http://127.0.0.1:4043" target="_blank">4043 - PainelDono</a>
  </div>

  <div class="footer">Veronica IA &mdash; Ecossistema de 7 produtos &mdash; {agora}</div>

  <script>
    function copiar(url, btn) {{
      navigator.clipboard.writeText(url).then(() => {{
        btn.textContent = 'Copiado!';
        btn.classList.add('copiado');
        setTimeout(() => {{ btn.textContent = 'Copiar'; btn.classList.remove('copiado'); }}, 2000);
      }});
    }}
  </script>
</body>
</html>"""

tmp = os.path.join(tempfile.gettempdir(), 'ngrok_veronica.html')
with open(tmp, 'w', encoding='utf-8') as f:
    f.write(html)

url_arquivo = 'file:///' + tmp.replace('\\', '/')
webbrowser.open(url_arquivo)
print(f'Pagina aberta: {tmp}')
print(f'Tuneis ativos: {ativos}/4')
