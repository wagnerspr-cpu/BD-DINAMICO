# Scraper Leo Madeiras - Deploy no Render

## Passos para Deploy:

### 1. Criar Repositório no GitHub
1. Acesse https://github.com/new
2. Nome do repositório: `leomadeiras-scraper`
3. Deixe como **Público**
4. Clique em "Create repository"

### 2. Upload dos Arquivos
1. Clique em "uploading an existing file"
2. Arraste os arquivos:
   - `app.py`
   - `requirements.txt`
   - `README.md`
3. Clique em "Commit changes"

### 3. Configurar no Render
1. Volte para o Render
2. Escolha **GitHub** como Git Provider
3. Conecte sua conta GitHub
4. Selecione o repositório `leomadeiras-scraper`
5. Configure:
   - **Name**: leomadeiras-scraper
   - **Region**: Ohio (US East)
   - **Branch**: main
   - **Root Directory**: deixe vazio
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

### 4. Deploy
1. Clique em "Create Web Service"
2. Aguarde o deploy (5-10 minutos)
3. Copie a URL que aparece (tipo: https://leomadeiras-scraper.onrender.com)

### 5. Passar a URL para o assistente
Depois do deploy, copie a URL e envie para o assistente implementar a integração.

## Testando a API

Após o deploy, teste com:
```bash
curl -X POST https://SUA-URL.onrender.com/buscar \
  -H "Content-Type: application/json" \
  -d '{"termo":"mdf branco","paginas":2}'
``