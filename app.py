import os
import json
import time
import re
import io
from datetime import datetime
from flask import Flask, render_template_string, request, send_file, redirect, url_for

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

app = Flask(__name__)

# --- CONFIGURAÇÃO DO DRIVER OTIMIZADA (MODO TURBO) ---
def get_driver():
    chrome_options = webdriver.ChromeOptions()
    
    # 1. Configurações Básicas para Servidor
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 2. BLOQUEIO DE IMAGENS E CSS (Acelera muito a busca)
    prefs = {
        "profile.managed_default_content_settings.images": 2,       # Bloqueia Imagens
        "profile.managed_default_content_settings.stylesheets": 2,  # Bloqueia Estilos (CSS)
        "profile.managed_default_content_settings.fonts": 2,        # Bloqueia Fontes
        "profile.default_content_setting_values.notifications": 2,  # Bloqueia Notificações
        "profile.managed_default_content_settings.popups": 2,       # Bloqueia Popups
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    # 3. Estratégia de Carregamento "Ansiosa"
    # Não espera carregar scripts pesados de fundo, libera o robô assim que o HTML chega.
    chrome_options.page_load_strategy = 'eager'

    # 4. Caminho do Chrome no Render
    if os.environ.get('RENDER'):
        chrome_binary_path = os.path.join(os.getcwd(), "chrome/opt/google/chrome/google-chrome")
        chrome_options.binary_location = chrome_binary_path
        service = Service() # Selenium Manager cuida do driver
    else:
        # Fallback para rodar no seu computador (se tiver webdriver-manager instalado)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
        except:
            service = Service()
    
    return webdriver.Chrome(service=service, options=chrome_options)

# --- INTERFACE WEB ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD Manager - Web Turbo</title>
    <style>
        body { background-color: #121212; color: white; font-family: sans-serif; text-align: center; padding: 20px; }
        .card { background-color: #252525; padding: 20px; margin: 15px auto; max-width: 500px; border-radius: 10px; border: 1px solid #333; }
        h1 { color: #E63946; }
        h2 { border-bottom: 2px solid #E63946; display: inline-block; padding-bottom: 5px; margin-bottom: 20px; }
        input, button { width: 90%; padding: 12px; margin: 5px 0; border-radius: 5px; border: none; }
        input[type="text"], input[type="number"] { background: #1A1A1A; color: white; border: 1px solid #555; }
        button { background-color: #E63946; color: white; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background-color: #C42B37; }
        .note { font-size: 0.8em; color: #aaa; margin-top: 5px; }
        .loading { display: none; color: #ffeb3b; font-weight: bold; margin-top: 15px; animation: piscar 1.5s infinite;}
        @keyframes piscar { 0% {opacity: 1;} 50% {opacity: 0.5;} 100% {opacity: 1;} }
    </style>
    <script>
        function showLoading() {
            document.getElementById('loading-msg').style.display = 'block';
            document.getElementById('btn-buscar').innerText = "BUSCANDO... AGUARDE";
            document.getElementById('btn-buscar').disabled = true;
            document.getElementById('btn-buscar').style.backgroundColor = "#555";
        }
    </script>
</head>
<body>
    <h1>BD MANAGER <span style="font-size:12px">TURBO</span></h1>

    <div class="card">
        <h2>1. Nova Coleta</h2>
        <form action="/coletar" method="post" onsubmit="showLoading()">
            <input type="text" name="termo" placeholder="Ex: MDF Branco" required>
            <div style="display:flex; justify-content:center; gap:10px; align-items:center;">
                <label>Páginas:</label>
                <input type="number" name="paginas" value="2" min="1" max="5" style="width: 60px;">
            </div>
            <button type="submit" id="btn-buscar">🚀 BUSCAR RÁPIDO</button>
            <p class="note">O robô está em modo rápido (sem imagens).</p>
            <p id="loading-msg" class="loading">⏳ Processando... Isso leva cerca de 30-60 segundos.</p>
        </form>
    </div>

    <div class="card">
        <h2>2. Atualizar Preços</h2>
        <form action="/atualizar" method="post" enctype="multipart/form-data">
            <label style="display:block; margin-bottom:5px;">Envie o JSON antigo:</label>
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
    if request.method == 'GET':
        return redirect(url_for('index'))

    termo = request.form.get('termo')
    try: paginas = int(request.form.get('paginas'))
    except: paginas = 1
    
    driver = None
    produtos = []
    
    try:
        driver = get_driver()
        url = f"https://www.leomadeiras.com.br/busca?q={termo}"
        driver.get(url)
        
        # Tempo reduzido (sem imagens carrega rápido)
        time.sleep(1.5)
        
        ids_vistos = set()
        
        for p in range(paginas):
            # Scroll rápido
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(0.5)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            if not links: break
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if not href or href in ids_vistos: continue
                    ids_vistos.add(href)
                    
                    match = re.search(r'/p/(\d+)', href)
                    codigo = match.group(1) if match else "S/C"
                    
                    # Tenta pegar o nome (Texto direto é mais rápido que atributo)
                    nome = link.text
                    if not nome:
                        try: nome = link.find_element(By.TAG_NAME, "img").get_attribute("alt")
                        except: nome = "Produto sem nome"
                    
                    preco = "Consulte"
                    try:
                        bloco = link.find_element(By.XPATH, "./ancestor::div[3]")
                        texto_bloco = bloco.text
                        if "R$" in texto_bloco:
                            linhas = texto_bloco.split('\n')
                            for linha in linhas:
                                if "R$" in linha and "à vista" not in linha:
                                    preco = linha.strip().replace("R$", "").strip()
                                    break
                    except: pass

                    produtos.append({
                        "id": codigo,
                        "nome": nome, 
                        "preco": f"R$ {preco}", 
                        "link": href, 
                        "data_update": datetime.now().strftime("%d/%m/%Y")
                    })
                except: continue
            
            # Paginação
            if p < paginas - 1:
                try:
                    prox = driver.find_elements(By.XPATH, f"//a[text()='{p+2}']")
                    if prox: 
                        driver.execute_script("arguments[0].click();", prox[0])
                        time.sleep(2) # Tempo seguro para troca de página
                    else: break
                except: break
            
    except Exception as e:
        return f"<h1>Erro técnico:</h1><p>{str(e)}</p><a href='/'>Voltar</a>"
    finally:
        if driver: 
            driver.quit()

    if produtos:
        buffer = io.BytesIO()
        buffer.write(json.dumps(produtos, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"coleta_{termo.replace(' ', '_')}.json",
            mimetype='application/json'
        )
    else:
        return "<h1>Nenhum produto encontrado.</h1><a href='/'>Voltar</a>"

@app.route('/atualizar', methods=['POST'])
def rota_atualizar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return "Erro"
    
    try:
        dados = json.load(arquivo)
        driver = get_driver()
        
        # Limite de segurança para plano gratuito (evita timeout de 2min)
        limite_itens = 40 
        contador = 0
        
        for produto in dados:
            if contador >= limite_itens: break
            try:
                driver.get(produto['link'])
                try:
                    # Espera muito curta pois CSS/IMG estão bloqueados
                    wait = webdriver.support.ui.WebDriverWait(driver, 3)
                    preco_el = wait.until(lambda d: d.find_element(By.CLASS_NAME, "vtex-store-components-3-x-currencyContainer"))
                    produto['preco'] = preco_el.text
                    produto['data_update'] = datetime.now().strftime("%d/%m/%Y")
                except: pass
                contador += 1
            except: pass
        
        driver.quit()
        
        buffer = io.BytesIO()
        buffer.write(json.dumps(dados, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="atualizado.json", mimetype='application/json')
    except Exception as e:
        return f"Erro: {e}"

@app.route('/unir', methods=['POST'])
def rota_unir():
    arquivos = request.files.getlist('arquivos')
    mega = []
    vistos = set()
    for arq in arquivos:
        try:
            dados = json.load(arq)
            for d in dados:
                link = d.get('link')
                if link not in vistos:
                    mega.append(d)
                    vistos.add(link)
        except: continue
    
    buffer = io.BytesIO()
    buffer.write(json.dumps(mega, indent=4, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="unificado.json", mimetype='application/json')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
