import os
import json
import time
import re
import io
from datetime import datetime
from flask import Flask, render_template_string, request, send_file, redirect, url_for
from bs4 import BeautifulSoup # Biblioteca nova para ler rápido

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

app = Flask(__name__)

# --- CONFIGURAÇÃO DO DRIVER (MÁXIMA VELOCIDADE) ---
def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Bloqueio total de visual para economizar CPU
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.popups": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.page_load_strategy = 'eager'

    if os.environ.get('RENDER'):
        chrome_binary_path = os.path.join(os.getcwd(), "chrome/opt/google/chrome/google-chrome")
        chrome_options.binary_location = chrome_binary_path
        service = Service()
    else:
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except: service = Service()
    
    return webdriver.Chrome(service=service, options=chrome_options)

# --- INTERFACE WEB ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD Manager - Ultra Fast</title>
    <style>
        body { background-color: #121212; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
        .card { background-color: #252525; padding: 20px; margin: 15px auto; max-width: 500px; border-radius: 10px; border: 1px solid #333; }
        h1 { color: #00E676; }
        h2 { border-bottom: 2px solid #00E676; display: inline-block; padding-bottom: 5px; margin-bottom: 20px; }
        input, button { width: 90%; padding: 12px; margin: 5px 0; border-radius: 5px; border: none; }
        input[type="text"], input[type="number"] { background: #1A1A1A; color: white; border: 1px solid #555; }
        button { background-color: #00E676; color: #000; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #00C853; }
        .note { font-size: 0.8em; color: #aaa; margin-top: 5px; }
        .loading { display: none; color: #00E676; font-weight: bold; margin-top: 15px;}
    </style>
    <script>
        function showLoading() {
            document.getElementById('loading-msg').style.display = 'block';
            document.getElementById('btn-buscar').innerText = "PROCESSANDO...";
            document.getElementById('btn-buscar').disabled = true;
        }
    </script>
</head>
<body>
    <h1>BD MANAGER <span style="font-size:12px">ULTRA</span></h1>

    <div class="card">
        <h2>1. Nova Coleta</h2>
        <form action="/coletar" method="post" onsubmit="showLoading()">
            <input type="text" name="termo" placeholder="Ex: MDF Branco" required>
            <div style="display:flex; justify-content:center; gap:10px; align-items:center;">
                <label>Páginas:</label>
                <input type="number" name="paginas" value="2" min="1" max="5" style="width: 60px;">
            </div>
            <button type="submit" id="btn-buscar">⚡ BUSCAR AGORA</button>
            <p id="loading-msg" class="loading">⏳ Extraindo dados em alta velocidade...</p>
        </form>
    </div>

    <div class="card">
        <h2>2. Atualizar Preços</h2>
        <form action="/atualizar" method="post" enctype="multipart/form-data">
            <input type="file" name="arquivo" accept=".json" required style="background:transparent; border:none;">
            <button type="submit">🔄 ATUALIZAR PREÇOS</button>
        </form>
    </div>

    <div class="card">
        <h2>3. Unir Arquivos</h2>
        <form action="/unir" method="post" enctype="multipart/form-data">
            <input type="file" name="arquivos" accept=".json" multiple required style="background:transparent; border:none;">
            <button type="submit">🔗 UNIR ARQUIVOS</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/coletar', methods=['GET', 'POST'])
def rota_coleta():
    if request.method == 'GET': return redirect(url_for('index'))
    
    termo = request.form.get('termo')
    try: paginas = int(request.form.get('paginas'))
    except: paginas = 1
    
    driver = None
    produtos = []
    
    try:
        driver = get_driver()
        driver.get(f"https://www.leomadeiras.com.br/busca?q={termo}")
        time.sleep(1.5) # Espera inicial curta
        
        ids_vistos = set()
        
        for p in range(paginas):
            # Scroll para forçar o carregamento dos itens (necessário pois o site usa Lazy Load)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1) # Espera o site reagir ao scroll
            
            # --- MÁGICA DE VELOCIDADE AQUI ---
            # Em vez de pedir elemento por elemento ao Selenium, pegamos o HTML todo
            # e processamos com BeautifulSoup (muito mais rápido)
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Procura todos os links que parecem produtos
            # O seletor 'a[href*="/p/"]' equivale ao XPath contains
            links = soup.select('a[href*="/p/"]')
            
            if not links: break
            
            for link in links:
                try:
                    href = link.get('href')
                    if not href: continue
                    
                    # Normaliza o link (às vezes vem relativo)
                    if not href.startswith('http'):
                        href = "https://www.leomadeiras.com.br" + href

                    if href in ids_vistos: continue
                    ids_vistos.add(href)
                    
                    # Extrai ID do link
                    match = re.search(r'/p/(\d+)', href)
                    codigo = match.group(1) if match else "S/C"
                    
                    # Tenta pegar o nome (Texto do link ou Alt da imagem)
                    nome = link.get_text(strip=True)
                    if not nome:
                        img = link.find('img')
                        if img: nome = img.get('alt', '')
                    if not nome: nome = "Produto sem nome"
                    
                    # Lógica de Preço via BeautifulSoup (Ancestrais)
                    preco = "Consulte"
                    # Sobe 3 níveis na árvore do HTML (equivalente ao ancestor::div[3])
                    parent = link.find_parent('div')
                    if parent: parent = parent.find_parent('div')
                    if parent: parent = parent.find_parent('div')
                    
                    if parent:
                        texto_bloco = parent.get_text(" ", strip=True)
                        if "R$" in texto_bloco:
                            # Procura o padrão de preço R$ 00,00
                            match_preco = re.search(r'R\$\s?[\d\.,]+', texto_bloco)
                            if match_preco:
                                preco = match_preco.group(0)

                    produtos.append({
                        "id": codigo,
                        "nome": nome, 
                        "preco": preco, 
                        "link": href, 
                        "data_update": datetime.now().strftime("%d/%m/%Y")
                    })
                except: continue
            
            # Paginação via Selenium (só clica se precisar)
            if p < paginas - 1:
                try:
                    # Tenta encontrar botão da próxima página via JS do Selenium
                    # O BS4 não clica, então voltamos ao driver rapidinho
                    driver.execute_script(f"""
                        var links = document.querySelectorAll('a');
                        for (var i = 0; i < links.length; i++) {{
                            if (links[i].innerText === '{p+2}') {{
                                links[i].click();
                                break;
                            }}
                        }}
                    """)
                    time.sleep(2)
                except: break

    except Exception as e:
        return f"<h1>Erro técnico:</h1><p>{str(e)}</p><a href='/'>Voltar</a>"
    finally:
        if driver: driver.quit()

    if produtos:
        buffer = io.BytesIO()
        buffer.write(json.dumps(produtos, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"coleta_{termo}.json", mimetype='application/json')
    return "<h1>Nada encontrado.</h1><a href='/'>Voltar</a>"

@app.route('/atualizar', methods=['POST'])
def rota_atualizar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return "Erro"
    
    try:
        dados = json.load(arquivo)
        driver = get_driver()
        contador = 0
        
        for produto in dados:
            if contador >= 50: break # Aumentei o limite um pouco
            try:
                driver.get(produto['link'])
                # BeautifulSoup para ler o preço rápido
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Tenta achar o container de preço (classe do vtex)
                preco_div = soup.find(class_="vtex-store-components-3-x-currencyContainer")
                if preco_div:
                    produto['preco'] = preco_div.get_text(strip=True)
                    produto['data_update'] = datetime.now().strftime("%d/%m/%Y")
                
                contador += 1
            except: pass
        
        driver.quit()
        buffer = io.BytesIO()
        buffer.write(json.dumps(dados, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="atualizado.json", mimetype='application/json')
    except Exception as e: return f"Erro: {e}"

@app.route('/unir', methods=['POST'])
def rota_unir():
    arquivos = request.files.getlist('arquivos')
    mega = []
    vistos = set()
    for arq in arquivos:
        try:
            dados = json.load(arq)
            for d in dados:
                if d.get('link') not in vistos:
                    mega.append(d)
                    vistos.add(d.get('link'))
        except: continue
    buffer = io.BytesIO()
    buffer.write(json.dumps(mega, indent=4, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="unificado.json", mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
