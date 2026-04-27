# COMO USAR — Verônica IA

Guia completo de uso de todos os painéis do ecossistema.

---

## Início Rápido

### Para iniciar TUDO com um clique:
```
Área de Trabalho → INICIAR_TUDO.bat
```
Isso abre 7 terminais (cada serviço) + abre o browser na página de status.

### Para iniciar produtos individuais:
| Arquivo na Área de Trabalho | O que faz |
|-----------------------------|-----------|
| `INICIAR_TUDO.bat` | Inicia todos os 6 serviços + abre status page |
| `INICIAR_PAINELGEST.bat` | Inicia PainelGest (5002) |
| `INICIAR_MOTOBOY.bat` | Inicia AppMotoboy (5003) |
| `INICIAR_FROTA.bat` | Inicia PainelFrota (5004) |
| `INICIAR_RESTAURANTE.bat` | Abre login do Restaurante no browser |
| `INICIAR_DONO.bat` | Abre login do Dono no browser |
| `BACKUP_DUPLO.bat` | Git push + backup nos 2 HDs externos |

---

## Página de Status

**URL:** http://localhost:5000

Mostra em tempo real:
- Status de cada serviço (verde = online / vermelho = offline)
- Links rápidos para cada painel
- Status dos provedores de IA (Ollama local, Groq, Gemini)
- Atualiza automaticamente a cada 15 segundos

---

## 1. Super Admin

**URL:** http://localhost:5002/super/login  
**Login:** `super` / `super123`

### O que pode fazer:
- **Dashboard:** MRR total, número de gestores por plano, receita
- **Gestores:** criar, editar, bloquear/desbloquear, excluir administradores
- **Planos:** definir preços dos planos (básico, profissional, premium)
- **Grupos de Motoboys:** vincular grupos ao PainelFrota, ver stats ao vivo
- **Cobrança por Grupo:** configurar modelo (por corrida ou mensalidade), lançar cobrança
- **Relatório Financeiro:** exportar PDF, enviar por email ao contador

### Fluxo para adicionar um restaurante:
1. Criar gestor (Admin) em **Gestores → Novo Gestor**
2. O gestor faz login em `/login` e cria o restaurante

---

## 2. Painel do Gestor (Admin)

**URL:** http://localhost:5002/login  
**Login:** `admin` / `admin123` (ou o que foi criado pelo Super Admin)

### O que pode fazer:
- **Dashboard:** resumo de clientes, restaurantes, vencimentos
- **Clientes:** gerenciar assinantes do SaaS
- **Restaurantes:** criar e gerenciar restaurantes vinculados
- **Redes Sociais:** cadastrar perfis para agendamento de posts
- **Agendamentos:** agendar posts no Instagram (via APScheduler)
- **Vencimentos:** controlar pagamentos e datas de vencimento
- **Cobranças:** gerar link de pagamento via Mercado Pago
- **Sub-Admins:** criar operadores com acesso limitado

---

## 3. Painel do Restaurante

**URL:** http://localhost:5002/restaurante/login  
**Login:** criado pelo Gestor

### O que pode fazer:
- **Dashboard:** resumo do dia, destaques do cardápio
- **Cardápio:** categorias, itens com preço, foto, promoção, disponibilidade
- **Kanban de Pedidos:** arraste pedidos entre colunas (Novo → Preparo → Pronto → Entregue)
- **CRM:** histórico de clientes, segmentação (VIP/Frequente/Inativo), notas
- **Vagas de Plantão:** abrir vagas para motoboys se inscreverem
- **Parceiros Motoboy:** gerenciar motoboys vinculados ao restaurante
- **Comprovante:** gerar comprovante de entrega para motoboy (PDF/email)
- **QR Frota:** gerar QR para conectar ao PainelFrota
- **Cardápio Público:** http://localhost:5002/cardapio/\<username\>

### Como usar o CRM:
1. Vá em **CRM Clientes**
2. Clique **Importar dos Pedidos** para popular automaticamente
3. Clientes são segmentados automaticamente:
   - **VIP:** 10+ pedidos OU ticket médio ≥ R$ 80
   - **Frequente:** 5+ pedidos
   - **Inativo:** último pedido há mais de 30 dias
4. Clique no cliente para ver histórico e adicionar notas

---

## 4. Painel do Dono

**URL:** http://localhost:5002/dono/login  
**Login:** `dono` / `dono123`

### O que pode fazer:
- **Dashboard:** 6 KPIs em tempo real (atualiza a cada 10s)
  - Pedidos hoje, Vendas hoje, Em andamento, Motoboys online, Funcionários, Restaurantes
- **Vendas:** tabela completa com **filtros por data, status e restaurante**
- **Pedidos Ativos:** lista com timer (auto-refresh 15s), alerta vermelho para pedidos > 30min
- **Funcionários:** gestores + sub-admins com status
- **Motoboys Online:** via integração com AppMotoboy (porta 5003)
- **Controle de Acesso:** log de todos os logins no sistema
- **Relatório:** gráfico de vendas 7 dias + totais do mês

### Como usar os filtros de Vendas:
1. Vá em **Vendas**
2. Use os campos: **Data** (calendario), **Status** (dropdown), **Restaurante** (dropdown)
3. Clique **Filtrar**
4. Para limpar, clique **Limpar**

---

## 5. AppMotoboy

**URL:** http://localhost:5003  
**Login:** `demo` / `demo123` (ou conta criada via QR)

### Como um motoboy se registra:
1. No PainelFrota, vá em **Motoboys → QR Code** do motoboy
2. O motoboy acessa: http://localhost:5003/registrar/\<token\>
3. Preenche nome, usuário e senha
4. Está vinculado à frota

### O que o motoboy pode fazer:
- **Dashboard:** toggle online/offline, GPS, entregas pendentes, saldo do dia
- **Entregas:** aceitar (15s para decidir), retirar, entregar, cancelar
  - Taxa automática: base + adicional chuva + pico + noturno
- **Vagas:** ver plantões abertos e se inscrever
- **Ganhos:** resumo dia / semana / mês / total acumulado
- **Histórico:** entregas anteriores
- **Turnos:** grade semanal de horas
- **Perfil:** dados pessoais, chave PIX para pagamento

---

## 6. PainelFrota

**URL:** http://localhost:5004  
**Login:** `admin` / `admin123`

### Níveis de acesso:
| Nível | Permissões |
|-------|-----------|
| `super` | Tudo (configurar, pagar, excluir) |
| `financeiro` | Ver financeiro e pagar motoboys |
| `operacional` | Criar entregas, gerenciar turnos |
| `visualizador` | Apenas visualizar |

### O que pode fazer:
- **Motoboys:** cadastrar, editar, gerar QR de vinculação, excluir
  - Modo de remuneração: por corrida (%) ou diária fixa
- **Restaurantes:** cadastrar restaurantes conectados via QR
- **Entregas:** criar manualmente, acompanhar status, finalizar
- **Financeiro:** ver saldo de cada motoboy, registrar pagamento PIX
- **Turnos:** abrir/encerrar turno por motoboy, histórico
- **Escala:** grade semanal com carga horária por motoboy
- **Mapa GPS:** posição em tempo real de todos os motoboys online
- **Relatórios:** gráficos de 14 dias, top motoboys, receita vs lucro
- **Admins:** criar operadores com diferentes níveis de acesso

### API pública do PainelFrota:
```
GET /api/stats         → { total_motoboys, corridas_hoje, receita_total }
GET /api/motoboy_token/<token> → dados do motoboy pelo token
```

---

## 7. Bot Verônica (Telegram)

**Bot:** @veronica_assistente_bot

### Comandos principais:
- `/start` — iniciar conversa
- `/perguntar <texto>` — fazer pergunta à IA
- `/marketing <produto>` — gerar post de marketing
- `/financeiro` — cotações de mercado
- `/imagem <descrição>` — gerar imagem
- `/lembrar <fato>` — salvar na memória permanente
- `/memorias` — ver o que foi salvo

---

## 8. API REST

**URL:** http://localhost:5001  
**Autenticação:** Header `X-API-Key: <sua_chave>`

```bash
# Status
curl -H "X-API-Key: SUA_CHAVE" http://localhost:5001/api/status

# Fazer pergunta
curl -X POST http://localhost:5001/api/perguntar \
  -H "X-API-Key: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"pergunta": "Olá!"}'

# Marketing
curl -X POST http://localhost:5001/api/marketing \
  -H "X-API-Key: SUA_CHAVE" \
  -H "Content-Type: application/json" \
  -d '{"produto": "Pizza de Calabresa"}'
```

---

## Backup

```
Área de Trabalho → BACKUP_DUPLO.bat
```

Faz 3 coisas automaticamente:
1. `git add . && git commit && git push` → GitHub
2. Copia para **HD G: (PainelGest)** em `G:\Backup_Veronica\veronica_<data>`
3. Copia para **HD E: (Veronica_IA)** em `E:\Backup_Veronica\veronica_<data>`

---

## Credenciais Padrão

| Sistema | Usuário | Senha | URL |
|---------|---------|-------|-----|
| Super Admin | `super` | `super123` | /super/login |
| Dono | `dono` | `dono123` | /dono/login |
| Gestor | `admin` | `admin123` | /login |
| PainelFrota | `admin` | `admin123` | localhost:5004 |
| AppMotoboy | `demo` | `demo123` | localhost:5003 |

> ⚠️ **Importante:** Altere as senhas padrão antes de usar em produção!

---

## Solução de Problemas

### "Página não carrega"
1. Verifique se o serviço está rodando (abra `http://localhost:5000`)
2. Execute o instalador correspondente na Área de Trabalho
3. Verifique se o Python está instalado: `python --version`

### "Erro no banco de dados"
```bash
cd painelgest
python -c "from app import app,db,migrate_db; ctx=app.app_context(); ctx.push(); db.create_all(); migrate_db()"
```

### "Bot Telegram não responde"
1. Verifique se `TELEGRAM_TOKEN` está no arquivo `.env`
2. Execute: `python main.py` e veja os erros no terminal

### "Backup falhou"
1. Verifique se os HDs estão conectados (G:\ e E:\)
2. Execute manualmente: `python organizar.py backup`
