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

# --- CONFIGURAÇÃO DO DRIVER (HEADLESS) ---
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--log-level=3")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

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
    </style>
</head>
<body>
    <h1>BD MANAGER <span style="font-size:12px">WEB</span></h1>
    <div class="card">
        <h2>1. Nova Coleta</h2>
        <form action="/coletar" method="post">
            <input type="text" name="termo" placeholder="Ex: MDF Branco" required>
            <input type="number" name="paginas" value="3" min="1" max="5">
            <button type="submit">🔍 BUSCAR E BAIXAR JSON</button>
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

@app.route('/coletar', methods=['POST'])
def rota_coleta():
    termo = request.form.get('termo')
    try: paginas = int(request.form.get('paginas'))
    except: paginas = 1
    
    driver = None
    produtos = []
    try:
        driver = get_driver()
        driver.get(f"https://www.leomadeiras.com.br/busca?q={termo}")
        time.sleep(2)
        ids_vistos = set()
        
        for p in range(paginas):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1.5)
            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            if not links: break
            
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href in ids_vistos: continue
                    ids_vistos.add(href)
                    
                    nome = link.text or link.find_element(By.TAG_NAME, "img").get_attribute("alt")
                    preco = "Consulte"
                    try:
                        bloco = link.find_element(By.XPATH, "./ancestor::div[3]")
                        if "R$" in bloco.text: preco = bloco.text.split("R$")[1].split("\n")[0].strip()
                    except: pass
                    
                    produtos.append({"nome": nome, "preco": f"R$ {preco}", "link": href, "data": datetime.now().strftime("%d/%m/%Y")})
                except: continue
            
            try:
                prox = driver.find_elements(By.XPATH, f"//a[text()='{p+2}']")
                if prox: 
                    driver.execute_script("arguments[0].click();", prox[0])
                    time.sleep(3)
                else: break
            except: break
            
    except Exception as e: return f"Erro: {str(e)}"
    finally:
        if driver: driver.quit()

    if produtos:
        buffer = io.BytesIO()
        buffer.write(json.dumps(produtos, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"coleta_{termo}.json", mimetype='application/json')
    return "Nada encontrado <a href='/'>Voltar</a>"

@app.route('/atualizar', methods=['POST'])
def rota_atualizar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return "Erro"
    dados = json.load(arquivo)
    driver = get_driver()
    try:
        for p in dados:
            try:
                driver.get(p['link'])
                time.sleep(1) # Rapido
                p['data'] = datetime.now().strftime("%d/%m/%Y")
            except: pass
    finally: driver.quit()
    
    buffer = io.BytesIO()
    buffer.write(json.dumps(dados, indent=4, ensure_ascii=False).encode('utf-8'))
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="atualizado.json", mimetype='application/json')

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
