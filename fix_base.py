caminho = "painelgest/templates/base.html"

with open(caminho, "r", encoding="utf-8") as f:
    linhas = f.readlines()

novas_linhas = []
for linha in linhas:
    linha = linha.replace("clientes_ifood", "clientes")
    linha = linha.replace("perfis_instagram_list", "perfis_instagram")
    linha = linha.replace("financeiro", "vencimentos")
    linha = linha.replace("ifood_list", "clientes")
    novas_linhas.append(linha)

with open(caminho, "w", encoding="utf-8") as f:
    f.writelines(novas_linhas)

print("Corrigido!")

# Verifica se ainda tem clientes_ifood
with open(caminho, "r", encoding="utf-8") as f:
    content = f.read()
if "clientes_ifood" in content:
    print("AINDA TEM clientes_ifood!")
else:
    print("Limpo! Sem clientes_ifood")