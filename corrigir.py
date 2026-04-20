# Adiciona funcao de transformar foto em anime no visao_geradora.py
codigo = open("modules/visao_geradora.py", "r", encoding="utf-8").read()

nova_funcao = '''
def transformar_foto_anime(caminho_imagem: str, estilo: str = "anime") -> tuple:
    """Transforma uma foto em estilo anime/cartoon usando IA"""
    try:
        import base64
        
        # Le a imagem e converte para base64
        with open(caminho_imagem, "rb") as f:
            imagem_b64 = base64.b64encode(f.read()).decode("utf-8")
        
        estilos = {
            "anime": "anime style, japanese animation, detailed anime art, Studio Ghibli style",
            "cartoon": "cartoon style, Disney animation, colorful cartoon, fun animated style",
            "pixar": "Pixar 3D animation style, detailed 3D cartoon, Pixar movie style",
            "sketch": "pencil sketch, black and white drawing, artistic sketch style",
            "watercolor": "watercolor painting, artistic, soft colors, painting style"
        }
        
        descricao_estilo = estilos.get(estilo.lower(), estilos["anime"])
        
        # Tenta usar DALL-E para transformacao
        try:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                client = openai.OpenAI(api_key=api_key)
                
                # Primeiro analisa a imagem
                response_analise = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Descreva detalhadamente esta imagem em ingles para eu recriar em estilo anime. Inclua: genero, cabelo, olhos, roupas, expressao, fundo. Seja muito detalhado."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_b64}"}}
                        ]
                    }],
                    max_tokens=300
                )
                
                descricao = response_analise.choices[0].message.content
                prompt_final = f"{descricao}, converted to {descricao_estilo}, high quality, detailed"
                
                # Gera a imagem no estilo solicitado
                response_img = client.images.generate(
                    model="dall-e-3",
                    prompt=prompt_final,
                    size="1024x1024",
                    quality="standard",
                    n=1
                )
                
                image_url = response_img.data[0].url
                r = requests.get(image_url, timeout=30)
                if r.status_code == 200:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    caminho = str(ASSETS_DIR / f"anime_{timestamp}.png")
                    with open(caminho, "wb") as f:
                        f.write(r.content)
                    return caminho, f"DALL-E 3 ({estilo})"
        except Exception as e:
            print(f"DALL-E falhou: {e}")
        
        # Fallback: Pollinations com descricao generica
        prompt = f"portrait photo transformed into {descricao_estilo}, high quality, detailed"
        caminho = gerar_imagem_pollinations(prompt)
        return caminho, f"Pollinations ({estilo})"
        
    except Exception as e:
        return f"ERRO: {e}", "erro"
'''

# Adiciona antes do final do arquivo
codigo = codigo + nova_funcao

with open("modules/visao_geradora.py", "w", encoding="utf-8") as f:
    f.write(codigo)
print("Funcao de transformacao adicionada!")