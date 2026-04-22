with open("painelgest/app.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    """@app.route('/dashboard')
def dashboard():
    if 'administrador' in session:
        return render_template('dashboard.html')
    else:
        return redirect(url_for('login'))""",
    """@app.route('/dashboard')
def dashboard():
    if 'administrador' in session:
        from datetime import date, timedelta
        clientes_total = Cliente.query.count()
        instagram_total = PerfilInstagram.query.count()
        hoje = date.today()
        em7dias = hoje + timedelta(days=7)
        vencimentos_proximos = Vencimento.query.filter(
            Vencimento.data_vencimento <= em7dias,
            Vencimento.status != 'pago'
        ).count()
        receita = sum([v.valor for v in Vencimento.query.filter_by(status='pago').all()])
        return render_template('dashboard.html',
            clientes_total=clientes_total,
            instagram_total=instagram_total,
            vencimentos_proximos=vencimentos_proximos,
            receita=f"{receita:,.0f}".replace(",",".")
        )
    else:
        return redirect(url_for('login'))"""
)

with open("painelgest/app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("app.py atualizado!")