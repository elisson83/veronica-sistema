import shutil
import os

# Copia o dashboard novo para o painelgest
src = "painelgest/templates/dashboard.html"

html = open(src, "r", encoding="utf-8").read() if os.path.exists(src) else ""

# Salva o novo dashboard profissional
novo_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PainelGest — Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg:#0a0c10;--surface:#111318;--surface2:#181c23;
    --border:rgba(255,255,255,0.07);--accent:#00e5a0;
    --accent2:#ff6b3d;--accent3:#7c6bff;--accent4:#ffd166;
    --text:#f0f2f7;--muted:#6b7280;--danger:#ff4d6d;
    --warn:#ffd166;--success:#00e5a0;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:var(--bg);color:var(--text);font-family:'DM Sans',sans-serif;display:flex;min-height:100vh;font-size:14px;}
  .sidebar{width:240px;background:var(--surface);border-right:1px solid var(--border);display:flex;flex-direction:column;padding:24px 0;position:fixed;height:100vh;z-index:100;}
  .logo{padding:0 24px 28px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--border);margin-bottom:16px;}
  .logo-icon{width:34px;height:34px;background:linear-gradient(135deg,var(--accent),var(--accent3));border-radius:10px;display:grid;place-items:center;font-size:16px;}
  .logo-text{font-family:'Syne',sans-serif;font-weight:800;font-size:18px;letter-spacing:-0.5px;}
  .logo-text span{color:var(--accent);}
  .nav-section{padding:8px 16px;font-size:10px;font-weight:600;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-top:8px;}
  .nav-item{display:flex;align-items:center;gap:12px;padding:10px 24px;color:var(--muted);cursor:pointer;transition:all .2s;position:relative;font-size:14px;text-decoration:none;}
  .nav-item:hover{color:var(--text);background:var(--surface2);}
  .nav-item.active{color:var(--accent);background:rgba(0,229,160,0.08);}
  .nav-item.active::before{content:'';position:absolute;left:0;top:4px;bottom:4px;width:3px;background:var(--accent);border-radius:0 4px 4px 0;}
  .nav-item .badge{margin-left:auto;background:var(--danger);color:#fff;font-size:10px;font-weight:700;padding:2px 7px;border-radius:20px;}
  .nav-item i{width:18px;text-align:center;font-size:15px;}
  .sidebar-footer{margin-top:auto;padding:16px 24px;border-top:1px solid var(--border);display:flex;align-items:center;gap:10px;}
  .avatar{width:34px;height:34px;background:linear-gradient(135deg,var(--accent3),var(--accent));border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:13px;}
  .user-info small{color:var(--muted);font-size:11px;display:block;}
  .main{margin-left:240px;flex:1;display:flex;flex-direction:column;min-height:100vh;}
  .topbar{background:var(--surface);border-bottom:1px solid var(--border);padding:14px 28px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:50;}
  .topbar-title{font-family:'Syne',sans-serif;font-weight:700;font-size:17px;}
  .topbar-sub{color:var(--muted);font-size:12px;}
  .topbar-actions{margin-left:auto;display:flex;gap:8px;}
  .btn{display:inline-flex;align-items:center;gap:7px;padding:9px 16px;border-radius:8px;border:none;cursor:pointer;font-family:'DM Sans',sans-serif;font-size:13px;font-weight:500;transition:all .2s;text-decoration:none;}
  .btn-primary{background:var(--accent);color:#000;font-weight:600;}
  .btn-primary:hover{background:#00fbb4;}
  .btn-ghost{background:var(--surface2);color:var(--text);border:1px solid var(--border);}
  .content{padding:28px;display:flex;flex-direction:column;gap:24px;}
  .alert-banner{background:linear-gradient(135deg,rgba(255,77,109,0.12),rgba(255,107,61,0.08));border:1px solid rgba(255,77,109,0.3);border-radius:12px;padding:14px 20px;display:flex;align-items:center;gap:14px;}
  .alert-dot{width:8px;height:8px;border-radius:50%;background:var(--danger);flex-shrink:0;}
  .alert-banner strong{color:var(--danger);}
  .alert-banner span{color:var(--muted);font-size:13px;}
  .alert-dismiss{margin-left:auto;cursor:pointer;color:var(--muted);font-size:18px;background:none;border:none;}
  .stats-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;}
  .stat-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:12px;transition:transform .2s;}
  .stat-card:hover{transform:translateY(-3px);}
  .stat-header{display:flex;align-items:center;justify-content:space-between;}
  .stat-icon{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;font-size:16px;}
  .ic-green{background:rgba(0,229,160,0.12);color:var(--accent);}
  .ic-orange{background:rgba(255,107,61,0.12);color:var(--accent2);}
  .ic-purple{background:rgba(124,107,255,0.12);color:var(--accent3);}
  .ic-yellow{background:rgba(255,209,102,0.12);color:var(--accent4);}
  .stat-badge{font-size:11px;padding:3px 8px;border-radius:20px;font-weight:600;}
  .badge-up{background:rgba(0,229,160,0.12);color:var(--accent);}
  .badge-down{background:rgba(255,77,109,0.12);color:var(--danger);}
  .stat-value{font-family:'Syne',sans-serif;font-size:30px;font-weight:800;letter-spacing:-1px;line-height:1;}
  .stat-label{color:var(--muted);font-size:12px;margin-top:2px;}
  .charts-row{display:grid;grid-template-columns:2fr 1fr;gap:16px;}
  .card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:22px;}
  .card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;}
  .card-title{font-family:'Syne',sans-serif;font-weight:700;font-size:15px;}
  .card-title small{display:block;color:var(--muted);font-family:'DM Sans',sans-serif;font-size:11px;font-weight:400;margin-top:2px;}
  canvas{max-height:220px;}
  .bottom-row{display:grid;grid-template-columns:1.4fr 1fr;gap:16px;}
  table{width:100%;border-collapse:collapse;}
  thead th{text-align:left;padding:8px 12px;font-size:11px;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:.8px;border-bottom:1px solid var(--border);}
  tbody tr{border-bottom:1px solid var(--border);transition:background .15s;}
  tbody tr:hover{background:var(--surface2);}
  td{padding:11px 12px;font-size:13px;}
  .client-name{font-weight:500;}
  .client-plan{font-size:12px;color:var(--muted);}
  .status-pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:600;}
  .pill-active{background:rgba(0,229,160,0.1);color:var(--accent);}
  .pill-warn{background:rgba(255,209,102,0.1);color:var(--warn);}
  .pill-danger{background:rgba(255,77,109,0.1);color:var(--danger);}
  .action-row{display:flex;gap:4px;}
  .icon-btn{width:28px;height:28px;border-radius:7px;border:none;cursor:pointer;display:grid;place-items:center;font-size:12px;transition:all .15s;}
  .icon-btn-edit{background:rgba(124,107,255,0.12);color:var(--accent3);}
  .icon-btn-charge{background:rgba(0,229,160,0.12);color:var(--accent);}
  .icon-btn-del{background:rgba(255,77,109,0.10);color:var(--danger);}
  .venc-list{display:flex;flex-direction:column;gap:10px;}
  .venc-item{display:flex;align-items:center;gap:12px;padding:12px;background:var(--surface2);border-radius:10px;border:1px solid var(--border);}
  .venc-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
  .venc-info{flex:1;}
  .venc-name{font-weight:500;font-size:13px;}
  .venc-date{font-size:11px;color:var(--muted);margin-top:2px;}
  .venc-days{font-size:11px;font-weight:600;white-space:nowrap;}
  .finance-row{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;}
  .finance-card{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:20px;}
  .finance-number{font-family:'Syne',sans-serif;font-size:24px;font-weight:800;letter-spacing:-1px;margin:8px 0 4px;}
  .finance-label{color:var(--muted);font-size:12px;}
  .finance-trend{font-size:11px;margin-top:6px;}
</style>
</head>
<body>
<aside class="sidebar">
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div class="logo-text">Painel<span>Gest</span></div>
  </div>
  <div class="nav-section">Principal</div>
  <a href="/dashboard" class="nav-item active"><i class="fas fa-grid-2"></i> Dashboard</a>
  <a href="/clientes" class="nav-item"><i class="fas fa-users"></i> Clientes</a>
  <a href="/vencimentos" class="nav-item"><i class="fas fa-calendar-clock"></i> Vencimentos</a>
  <div class="nav-section">Canais</div>
  <a href="/perfis_instagram" class="nav-item"><i class="fab fa-instagram"></i> Instagram</a>
  <div class="nav-section">Financeiro</div>
  <a href="/vencimentos" class="nav-item"><i class="fas fa-chart-line"></i> Faturamento</a>
  <div class="nav-section">Sistema</div>
  <a href="/logout" class="nav-item"><i class="fas fa-sign-out-alt"></i> Sair</a>
  <div class="sidebar-footer">
    <div class="avatar">AD</div>
    <div class="user-info">
      <strong>Admin</strong>
      <small>PainelGest</small>
    </div>
  </div>
</aside>
<main class="main">
  <header class="topbar">
    <div>
      <div class="topbar-title">Dashboard</div>
      <div class="topbar-sub">Bem-vindo ao PainelGest</div>
    </div>
    <div class="topbar-actions">
      <a href="/cadastrar_cliente" class="btn btn-primary"><i class="fas fa-user-plus"></i> Novo Cliente</a>
    </div>
  </header>
  <div class="content">
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon ic-green"><i class="fas fa-users"></i></div>
          <span class="stat-badge badge-up">Ativos</span>
        </div>
        <div>
          <div class="stat-value">{{ clientes_total }}</div>
          <div class="stat-label">Clientes iFood</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon ic-purple"><i class="fab fa-instagram"></i></div>
          <span class="stat-badge badge-up">Online</span>
        </div>
        <div>
          <div class="stat-value">{{ instagram_total }}</div>
          <div class="stat-label">Perfis Instagram</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon ic-yellow"><i class="fas fa-triangle-exclamation"></i></div>
          <span class="stat-badge badge-down">Atenção</span>
        </div>
        <div>
          <div class="stat-value">{{ vencimentos_proximos }}</div>
          <div class="stat-label">Vencendo em breve</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-icon ic-orange"><i class="fas fa-circle-dollar-to-slot"></i></div>
          <span class="stat-badge badge-up">Mês</span>
        </div>
        <div>
          <div class="stat-value">R${{ receita }}</div>
          <div class="stat-label">Receita Mensal</div>
        </div>
      </div>
    </div>
  </div>
</main>
<script>
</script>
</body>
</html>"""

with open("painelgest/templates/dashboard.html", "w", encoding="utf-8") as f:
    f.write(novo_html)
print("Dashboard profissional salvo!")