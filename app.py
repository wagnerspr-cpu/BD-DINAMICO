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

# --- CONFIGURAÇÃO DO DRIVER (Mantida a lógica headless) ---
def get_driver():
    options = webdriver.ChromeOptions()
    # Configurações essenciais para rodar em servidor (Render/Linux)
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("--log-level=3")
    
    # Tenta usar o Chrome instalado pelo Render ou localmente
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- TEMPLATE HTML (Interface Web Simples) ---
# Isso cria a interface visual direto no navegador
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>BD Manager - Web Edition</title>
    <style>
        body { background-color: #121212; color: #FFFFFF; font-family: sans-serif; padding: 20px; text-align: center; }
        .card { background-color: #252525; border: 1px solid #333; padding: 20px; margin: 20px auto; max-width: 600px; border-radius: 10px; }
        h1 { color: #E63946; }
        h2 { color: #E63946; border-bottom: 2px solid #E63946; display: inline-block; padding-bottom: 5px; }
        input, button { padding: 10px; margin: 5px; border-radius: 5px; border: none; }
        input[type="text"], input[type="number"] { width: 70%; background: #1A1A1A; color: white; border: 1px solid #555; }
        button { background-color: #E63946; color: white; font-weight: bold; cursor: pointer; width: 100%; }
        button:hover { background-color: #C42B37; }
        .log { background-color: #0A0A0A; color: #00FF00; padding: 10px; text-align: left; font-family: monospace; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>BD MANAGER <span style="font-size:12px">vWeb</span></h1>

    <div class="card">
        <h2>1. Nova Coleta</h2>
        <form action="/coletar" method="post">
            <input type="text" name="termo" placeholder="Ex: MDF Branco" required><br>
            <label>Páginas:</label> <input type="number" name="paginas" value="3" min="1" max="10" style="width: 50px;"><br><br>
            <button type="submit">INICIAR BUSCA E BAIXAR JSON</button>
        </form>
    </div>

    <div class="card">
        <h2>2. Atualizar Preços</h2>
        <form action="/atualizar" method="post" enctype="multipart/form-data">
            <label>Subir JSON antigo:</label><br>
            <input type="file" name="arquivo" accept=".json" required><br><br>
            <button type="submit">ATUALIZAR PREÇOS</button>
        </form>
    </div>

    <div class="card">
        <h2>3. Unir Arquivos</h2>
        <form action="/unir" method="post" enctype="multipart/form-data">
            <label>Selecione vários arquivos JSON:</label><br>
            <input type="file" name="arquivos" accept=".json" multiple required><br><br>
            <button type="submit">UNIR E BAIXAR</button>
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
    try:
        paginas = int(request.form.get('paginas'))
    except:
        paginas = 1

    if not termo:
        return "Erro: Termo necessário"

    driver = None
    produtos_encontrados = []
    
    try:
        driver = get_driver()
        # Lógica original de busca
        url = f"https://www.leomadeiras.com.br/busca?q={termo}"
        driver.get(url)
        time.sleep(3)
        
        ids_vistos = set()
        pagina_atual = 1
        
        while pagina_atual <= paginas:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)

            links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
            
            novos_nesta_pag = 0
            for link in links:
                try:
                    href = link.get_attribute("href")
                    match = re.search(r'/p/(\d+)', href)
                    codigo = match.group(1) if match else None
                    
                    if not codigo or codigo in ids_vistos: continue
                    
                    nome = link.text or link.find_element(By.TAG_NAME, "img").get_attribute("alt")
                    
                    preco = "Consulte"
                    try:
                        bloco = link.find_element(By.XPATH, "./ancestor::div[3]")
                        if "R$" in bloco.text:
                            for linha in bloco.text.split('\n'):
                                if "R$" in linha and "à vista" not in linha:
                                    preco = linha.strip()
                                    break
                    except: pass

                    if codigo and nome:
                        produtos_encontrados.append({
                            "id": codigo, "nome": nome, "preco": preco, 
                            "link": href, "data_update": datetime.now().strftime("%d/%m/%Y")
                        })
                        ids_vistos.add(codigo)
                        novos_nesta_pag += 1
                except: continue
            
            if novos_nesta_pag == 0 and pagina_atual > 1: break
            
            if pagina_atual < paginas:
                try:
                    prox = driver.find_elements(By.XPATH, f"//a[text()='{pagina_atual+1}']")
                    if prox: 
                        driver.execute_script("arguments[0].click();", prox[0])
                        time.sleep(4)
                        pagina_atual += 1
                    else: break
                except: break
            else: break
            
    except Exception as e:
        return f"Erro durante a coleta: {str(e)}"
    finally:
        if driver: driver.quit()

    # Prepara o download
    if produtos_encontrados:
        nome_arquivo = f"coleta_{termo.replace(' ', '_')}.json"
        
        # Cria o arquivo em memória para download
        buffer = io.BytesIO()
        buffer.write(json.dumps(produtos_encontrados, indent=4, ensure_ascii=False).encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/json'
        )
    else:
        return "Nenhum produto encontrado. Tente outro termo."

# ================= 2. ROTA DE ATUALIZAR =================
@app.route('/atualizar', methods=['POST'])
def rota_atualizar():
    arquivo = request.files.get('arquivo')
    if not arquivo: return "Nenhum arquivo enviado"

    try:
        dados = json.load(arquivo)
        driver = get_driver()
        atualizados = []
        
        for produto in dados:
            try:
                driver.get(produto['link'])
                try:
                    wait = webdriver.support.ui.WebDriverWait(driver, 5)
                    preco_el = wait.until(lambda d: d.find_element(By.CLASS_NAME, "vtex-store-components-3-x-currencyContainer"))
                    novo_preco = preco_el.text
                except:
                    novo_preco = "Indisponível"
                
                produto['preco'] = novo_preco
                produto['data_update'] = datetime.now().strftime("%d/%m/%Y")
                atualizados.append(produto)
            except:
                atualizados.append(produto)
        
        driver.quit()
        
        buffer = io.BytesIO()
        buffer.write(json.dumps(atualizados, indent=4, ensure_ascii=False).encode('utf-8'))
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
    if not arquivos: return "Nenhum arquivo enviado"

    mega_lista = []
    ids_existentes = set()
    
    for arquivo in arquivos:
        try:
            dados = json.load(arquivo)
            for item in dados:
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
    # Importante: host='0.0.0.0' é necessário para o Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
