import os
import json
import time
import re
import io
from datetime import datetime
from flask import Flask, render_template_string, request, send_file

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

app = Flask(__name__)

# --- CONFIGURAÇÃO DO DRIVER (CORRIGIDA PARA O RENDER) ---
def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # SE ESTIVER RODANDO NO SERVIDOR DO RENDER
    if os.environ.get('RENDER'):
        # Aponta para a pasta onde o "comando gigante" instalou o Chrome
        chrome_binary_path = os.path.join(os.getcwd(), "chrome/opt/google/chrome/google-chrome")
        chrome_options.binary_location = chrome_binary_path
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# --- INTERFACE WEB (HTML) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD Manager - Web</title>
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
    </style>
</head>
<body>
    <h1>BD MANAGER <span style="font-size:12px">WEB</span></h1>

    <div class="card">
        <h2>1. Nova Coleta</h2>
        <form action="/coletar" method="post">
            <input type="text" name="termo" placeholder="Ex: MDF Branco" required>
            <div style="display:flex; justify-content:center; gap:10px; align-items:center;">
                <label>Páginas:</label>
                <input type="number" name="paginas" value="3" min="1" max="5" style="width: 60px;">
            </div>
            <button type="submit">🔍 BUSCAR E BAIXAR JSON</button>
            <p class="note">Isso pode levar alguns segundos. Não feche a página.</p>
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
            <label style="display:block; margin-bottom:5px;">Selecione vários JSONs:</label>
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

# ================= 1. ROTA DE COLETA =================
@app.route('/coletar', methods=['POST'])
def rota_coleta():
    termo = request.form.get('termo')
    try: paginas = int(request.form.get('paginas'))
    except: paginas = 1
    
    driver = None
    produtos = []
    
    try:
        driver = get_driver()
        url = f"https://www.leomadeiras.com.br/busca?q={termo}"
        driver.get(url)
        time.sleep(2)
        
        ids_vistos = set()
        
        for p in range(paginas):
            # Scroll para carregar itens
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1.5)

            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            if not links: break
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    # Evita duplicados e links inválidos
                    if not href or href in ids_vistos: continue
                    ids_vistos.add(href)
                    
                    match = re.search(r'/p/(\d+)', href)
                    codigo = match.group(1) if match else "S/C"
                    
                    nome = link.text or link.find_element(By.TAG_NAME, "img").get_attribute("alt")
                    
                    preco = "Consulte"
                    try:
                        bloco = link.find_element(By.XPATH, "./ancestor::div[3]")
                        if "R$" in bloco.text:
                            # Pega o preço limpo
                            preco = bloco.text.split("R$")[1].split("\n")[0].strip()
                    except: pass

                    produtos.append({
                        "id": codigo,
                        "nome": nome, 
                        "preco": f"R$ {preco}" if "Consulte" not in preco else preco, 
                        "link": href, 
                        "data_update": datetime.now().strftime("%d/%m/%Y")
                    })
                except: continue
            
            # Tenta ir para a próxima página
            try:
                # Procura botão da página seguinte (ex: se estou na 1, procuro o 2)
                prox = driver.find_elements(By.XPATH, f"//a[text()='{p+2}']")
                if prox: 
                    driver.execute_script("arguments[0].click();", prox[0])
                    time.sleep(3)
                else: break
            except: break
            
    except Exception as e:
        return f"<h1>Erro:</h1><p>{str(e)}</p>"
    finally:
        if driver: driver.quit()

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

# ================= 2. ROTA DE ATUALIZAR =================
@app.route('/atualizar', methods=['POST'])
def rota_atualizar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return "Erro: Nenhum arquivo enviado"

    try:
        dados = json.load(arquivo)
        driver = get_driver()
        
        for produto in dados:
            try:
                driver.get(produto['link'])
                try:
                    # Espera rápida para ver se o preço aparece
                    wait = webdriver.support.ui.WebDriverWait(driver, 5)
                    preco_el = wait.until(lambda d: d.find_element(By.CLASS_NAME, "vtex-store-components-3-x-currencyContainer"))
                    novo_preco = preco_el.text
                except:
                    novo_preco = "Indisponível"
                
                produto['preco'] = novo_preco
                produto['data_update'] = datetime.now().strftime("%d/%m/%Y")
            except:
                pass # Mantém o antigo se der erro
        
        driver.quit()
        
        buffer = io.BytesIO()
        buffer.write(json.dumps(dados, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"atualizado_{int(time.time())}.json",
            mimetype='application/json'
        )
    except Exception as e:
        return f"Erro ao atualizar: {str(e)}"

# ================= 3. ROTA DE UNIR =================
@app.route('/unir', methods=['POST'])
def rota_unir():
    arquivos = request.files.getlist('arquivos')
    if not arquivos: return "Erro: Nenhum arquivo enviado"

    mega_lista = []
    ids_existentes = set()
    
    for arquivo in arquivos:
        try:
            dados = json.load(arquivo)
            for item in dados:
                # Usa o link ou ID como chave única
                chave = item.get('id', item.get('link'))
                if chave not in ids_existentes:
                    mega_lista.append(item)
                    ids_existentes.add(chave)
        except: continue

    buffer = io.BytesIO()
    buffer.write(json.dumps(mega_lista, indent=4, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"unificado_{int(time.time())}.json",
        mimetype='application/json'
    )

if __name__ == "__main__":
    # Importante: Pega a porta do Render ou usa 5000 localmente
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
