import customtkinter as ctk
import threading
import sys
import os
import json
import time
import re
import traceback
from tkinter import filedialog
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- PALETA DE CORES "RED EDITION" ---
CORES = {
    "bg_root": "#121212",         # Fundo principal
    "bg_menu": "#1A1A1A",         # Menu lateral
    "bg_card": "#252525",         # Cartões
    "borda": "#333333",           # Bordas sutis
    "accent_red": "#E63946",      # VERMELHO DESTAQUE
    "accent_hover": "#C42B37",    # Vermelho escuro (hover)
    "text_white": "#FFFFFF",      # Texto principal
    "text_gray": "#B0B0B0",       # Texto secundário
    "log_bg": "#0A0A0A",          # Terminal preto
    "success_green": "#2ecc71"    # Verde auxiliar
}

ctk.set_appearance_mode("Dark")

class AppBDDinamico(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuração da Janela
        self.title("BD Dinamico v5.1 - Red Edition (Fixed)") 
        self.geometry("1000x700")
        self.resizable(False, False)
        self.configure(fg_color=CORES["bg_root"])
        
        # Variáveis
        self.produtos_temp = []
        self.check_vars = []
        self.termo_usado = ""
        self.arquivo_para_atualizar = ""

        # --- GRID PRINCIPAL ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 1. MENU LATERAL
        self.frame_menu = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=CORES["bg_menu"])
        self.frame_menu.grid(row=0, column=0, sticky="nswe")
        
        self.label_logo = ctk.CTkLabel(self.frame_menu, text="BD MANAGER", font=("Montserrat", 26, "bold"), text_color=CORES["text_white"])
        self.label_logo.grid(row=0, column=0, padx=20, pady=(50, 10))
        
        self.linha_accent = ctk.CTkFrame(self.frame_menu, height=4, width=100, fg_color=CORES["accent_red"], corner_radius=2)
        self.linha_accent.grid(row=1, column=0, pady=(0, 40))

        # Botões Menu
        self.btn_menu_coletar = self.criar_botao_menu("Nova Coleta", "coletar", 2)
        self.btn_menu_atualizar = self.criar_botao_menu("Atualizar Preços", "atualizar", 3)
        self.btn_menu_unir = self.criar_botao_menu("Unir Arquivos", "unir", 4)

        self.lbl_versao = ctk.CTkLabel(self.frame_menu, text="v5.1 Stable", text_color=CORES["text_gray"], font=("Roboto", 11))
        self.lbl_versao.grid(row=10, column=0, pady=30, sticky="s")
        self.frame_menu.grid_rowconfigure(10, weight=1)

        # 2. CONTEÚDO
        self.frame_conteudo = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frame_conteudo.grid(row=0, column=1, sticky="nswe", padx=40, pady=40)

        self.criar_tela_coletar()
        self.criar_tela_atualizar()
        self.criar_tela_unir()

        self.mudar_tela("coletar")

    def criar_botao_menu(self, texto, tela, linha):
        btn = ctk.CTkButton(
            self.frame_menu, 
            text=texto, 
            command=lambda: self.mudar_tela(tela),
            fg_color="transparent", 
            hover_color=CORES["bg_card"], 
            height=55,
            anchor="w",
            font=("Montserrat", 14, "bold"),
            corner_radius=12,
            text_color=CORES["text_gray"]
        )
        btn.grid(row=linha, column=0, padx=15, pady=10, sticky="ew")
        return btn

    def mudar_tela(self, nome_tela):
        self.frame_coletar.pack_forget()
        self.frame_atualizar.pack_forget()
        self.frame_unir.pack_forget()
        
        for btn in [self.btn_menu_coletar, self.btn_menu_atualizar, self.btn_menu_unir]:
            btn.configure(fg_color="transparent", text_color=CORES["text_gray"])

        if nome_tela == "coletar":
            self.frame_coletar.pack(fill="both", expand=True)
            self.btn_menu_coletar.configure(fg_color=CORES["accent_red"], text_color=CORES["text_white"], hover_color=CORES["accent_hover"])
        elif nome_tela == "atualizar":
            self.frame_atualizar.pack(fill="both", expand=True)
            self.btn_menu_atualizar.configure(fg_color=CORES["accent_red"], text_color=CORES["text_white"], hover_color=CORES["accent_hover"])
        elif nome_tela == "unir":
            self.frame_unir.pack(fill="both", expand=True)
            self.btn_menu_unir.configure(fg_color=CORES["accent_red"], text_color=CORES["text_white"], hover_color=CORES["accent_hover"])

    # ================= TELA 1: COLETAR =================
    def criar_tela_coletar(self):
        self.frame_coletar = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        
        ctk.CTkLabel(self.frame_coletar, text="PESQUISAR PRODUTOS", font=("Montserrat", 28, "bold"), text_color=CORES["text_white"]).pack(anchor="w", pady=(0, 25))

        card_busca = ctk.CTkFrame(self.frame_coletar, fg_color=CORES["bg_card"], border_width=2, border_color=CORES["borda"], corner_radius=16)
        card_busca.pack(fill="x", pady=15, ipady=10)

        ctk.CTkLabel(card_busca, text="Termo de Busca:", font=("Roboto", 14, "bold"), text_color=CORES["text_white"]).pack(anchor="w", padx=25, pady=(25, 8))
        self.entry_busca = ctk.CTkEntry(card_busca, placeholder_text="Ex: MDF Branco TX 15mm", height=45, 
                                        fg_color=CORES["bg_root"], border_color=CORES["borda"], text_color=CORES["text_white"], corner_radius=8)
        self.entry_busca.pack(fill="x", padx=25, pady=(0, 25))

        ctk.CTkLabel(card_busca, text="Profundidade (Páginas):", font=("Roboto", 14, "bold"), text_color=CORES["text_white"]).pack(anchor="w", padx=25, pady=(0, 8))
        self.slider_paginas = ctk.CTkSlider(card_busca, from_=1, to=10, number_of_steps=9, 
                                            progress_color=CORES["accent_red"], button_color=CORES["accent_red"], button_hover_color=CORES["accent_hover"])
        self.slider_paginas.set(3)
        self.slider_paginas.pack(fill="x", padx=25, pady=(0, 10))
        
        self.lbl_pag_valor = ctk.CTkLabel(card_busca, text="3 páginas", text_color=CORES["text_gray"])
        self.lbl_pag_valor.pack(pady=(0, 20))
        self.slider_paginas.configure(command=lambda v: self.lbl_pag_valor.configure(text=f"{int(v)} páginas"))

        self.btn_iniciar_coleta = ctk.CTkButton(self.frame_coletar, text="INICIAR BUSCA", command=self.thread_coleta, 
                                                height=60, fg_color=CORES["accent_red"], hover_color=CORES["accent_hover"], 
                                                font=("Montserrat", 16, "bold"), corner_radius=12)
        self.btn_iniciar_coleta.pack(fill="x", pady=25)

        ctk.CTkLabel(self.frame_coletar, text="CONSOLE DO SISTEMA:", text_color=CORES["text_gray"], font=("Roboto", 12, "bold")).pack(anchor="w", pady=(10,5))
        self.log_coleta = ctk.CTkTextbox(self.frame_coletar, fg_color=CORES["log_bg"], text_color=CORES["text_white"], 
                                         height=120, corner_radius=8, border_width=1, border_color=CORES["borda"], font=("Consolas", 13))
        self.log_coleta.pack(fill="both", expand=True)
        self.log_coleta.insert("0.0", "> Sistema pronto. Aguardando comando...\n")
        self.log_coleta.configure(state="disabled")

    # ================= TELA 2: ATUALIZAR =================
    def criar_tela_atualizar(self):
        self.frame_atualizar = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        ctk.CTkLabel(self.frame_atualizar, text="ATUALIZAR PREÇOS", font=("Montserrat", 28, "bold"), text_color=CORES["text_white"]).pack(anchor="w", pady=(0, 25))

        card = ctk.CTkFrame(self.frame_atualizar, fg_color=CORES["bg_card"], border_width=2, border_color=CORES["borda"], corner_radius=16)
        card.pack(fill="x", pady=15, ipady=20)

        ctk.CTkLabel(card, text="SELECIONE A BASE DE DADOS (.JSON):", font=("Roboto", 14, "bold"), text_color=CORES["text_white"]).pack(anchor="w", padx=25, pady=(10, 15))
        
        self.btn_carregar_json = ctk.CTkButton(card, text="Carregar Arquivo JSON...", command=self.selecionar_json_update, 
                                                fg_color=CORES["bg_root"], border_width=1, border_color=CORES["accent_red"], 
                                                hover_color=CORES["bg_menu"], height=50, font=("Roboto", 14))
        self.btn_carregar_json.pack(fill="x", padx=25, pady=10)

        self.lbl_arquivo_selecionado = ctk.CTkLabel(card, text="Nenhum arquivo selecionado", text_color=CORES["text_gray"])
        self.lbl_arquivo_selecionado.pack(pady=(5, 0))

        self.btn_iniciar_update = ctk.CTkButton(self.frame_atualizar, text="ATUALIZAR AGORA", command=self.thread_update, state="disabled", 
                                                height=60, fg_color=CORES["accent_red"], hover_color=CORES["accent_hover"], 
                                                font=("Montserrat", 16, "bold"), corner_radius=12)
        self.btn_iniciar_update.pack(fill="x", pady=25)

        self.log_update = ctk.CTkTextbox(self.frame_atualizar, fg_color=CORES["log_bg"], text_color=CORES["text_white"], 
                                         height=120, corner_radius=8, border_width=1, border_color=CORES["borda"], font=("Consolas", 13))
        self.log_update.pack(fill="both", expand=True)
        self.log_update.configure(state="disabled")

    # ================= TELA 3: UNIR =================
    def criar_tela_unir(self):
        self.frame_unir = ctk.CTkFrame(self.frame_conteudo, fg_color="transparent")
        ctk.CTkLabel(self.frame_unir, text="UNIR BASES DE DADOS", font=("Montserrat", 28, "bold"), text_color=CORES["text_white"]).pack(anchor="w", pady=(0, 25))

        card = ctk.CTkFrame(self.frame_unir, fg_color=CORES["bg_card"], border_width=2, border_color=CORES["borda"], corner_radius=16)
        card.pack(fill="x", pady=15, ipady=30)

        ctk.CTkLabel(card, text="MÚLTIPLOS ARQUIVOS -> ARQUIVO ÚNICO", font=("Roboto", 16, "bold"), text_color=CORES["accent_red"]).pack(pady=(0,10))
        ctk.CTkLabel(card, text="Esta ferramenta funde vários arquivos JSON, removendo duplicatas automaticamente.", 
                     wraplength=500, justify="center", text_color=CORES["text_gray"], font=("Roboto", 13)).pack(pady=(0, 30), padx=20)

        self.btn_selecionar_varios = ctk.CTkButton(self.frame_unir, text="SELECIONAR ARQUIVOS PARA UNIR", command=self.executar_uniao, 
                                                    height=60, fg_color=CORES["accent_red"], hover_color=CORES["accent_hover"], 
                                                    font=("Montserrat", 16, "bold"), corner_radius=12)
        self.btn_selecionar_varios.pack(fill="x", pady=25)

        self.log_unir = ctk.CTkTextbox(self.frame_unir, fg_color=CORES["log_bg"], text_color=CORES["text_white"], 
                                         height=150, corner_radius=8, border_width=1, border_color=CORES["borda"], font=("Consolas", 13))
        self.log_unir.pack(fill="both", expand=True)
        self.log_unir.configure(state="disabled")

    # ================= LOG SYSTEM =================
    def escrever_log(self, widget, msg, limpar=False):
        widget.configure(state="normal")
        if limpar: widget.delete("0.0", "end")
        timestamp = datetime.now().strftime('%H:%M:%S')
        widget.insert("end", f"> [{timestamp}] {msg}\n")
        widget.see("end")
        widget.configure(state="disabled")

    # ================= DRIVER SETUP =================
    def get_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled") 
        options.add_argument("--log-level=3")
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # ================= COLETA =================
    def thread_coleta(self):
        threading.Thread(target=self.rodar_coleta).start()

    def rodar_coleta(self):
        termo = self.entry_busca.get()
        paginas = int(self.slider_paginas.get())
        
        if not termo: 
            self.escrever_log(self.log_coleta, "ERRO: Digite um termo para buscar.")
            return

        self.btn_iniciar_coleta.configure(state="disabled", text="PROCESSANDO...", fg_color=CORES["bg_card"])
        self.escrever_log(self.log_coleta, f"Iniciando busca por: '{termo}'...", limpar=True)
        
        driver = None
        self.produtos_temp = []
        self.termo_usado = termo
        
        try:
            driver = self.get_driver()
            url = f"https://www.leomadeiras.com.br/busca?q={termo}"
            driver.get(url)
            time.sleep(3)
            
            ids_vistos = set()
            pagina_atual = 1
            
            while pagina_atual <= paginas:
                self.escrever_log(self.log_coleta, f"Lendo página {pagina_atual} de {paginas}...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)

                links = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
                novos = 0

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
                            self.produtos_temp.append({
                                "id": codigo, "nome": nome, "preco": preco, 
                                "link": href, "data_update": datetime.now().strftime("%d/%m/%Y")
                            })
                            ids_vistos.add(codigo)
                            novos += 1
                    except: continue

                if novos == 0 and pagina_atual > 1: break
                
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

            if self.produtos_temp:
                self.escrever_log(self.log_coleta, "Busca finalizada. Selecione os itens na janela.")
                # Usa 'after' para garantir que rode na thread principal da GUI
                self.after(0, self.abrir_popup_selecao)
            else:
                self.escrever_log(self.log_coleta, "Nenhum produto encontrado.")
                self.btn_iniciar_coleta.configure(state="normal", text="INICIAR BUSCA", fg_color=CORES["accent_red"])

        except Exception as e:
            self.escrever_log(self.log_coleta, f"Erro: {e}")
            self.btn_iniciar_coleta.configure(state="normal", text="INICIAR BUSCA", fg_color=CORES["accent_red"])
        finally:
            if driver: driver.quit()

    # ================= POPUP SELEÇÃO (CORRIGIDO) =================
    def abrir_popup_selecao(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Filtrar Resultados")
        popup.geometry("850x700")
        popup.configure(fg_color=CORES["bg_root"]) 
        popup.attributes("-topmost", True)
        
        # --- CORREÇÃO DO TRAVAMENTO ---
        # Função para liberar o botão da tela principal ao fechar o popup
        def ao_fechar():
            self.btn_iniciar_coleta.configure(state="normal", text="INICIAR BUSCA", fg_color=CORES["accent_red"])
            popup.destroy()

        # Vincula o evento de fechar janela ("X") à função de destravamento
        popup.protocol("WM_DELETE_WINDOW", ao_fechar)

        # Cabeçalho
        header_frame = ctk.CTkFrame(popup, fg_color=CORES["bg_menu"], corner_radius=0, height=80)
        header_frame.pack(fill="x")
        
        ctk.CTkLabel(header_frame, text=f"RESULTADOS DA BUSCA", font=("Montserrat", 20, "bold"), text_color=CORES["text_white"]).pack(pady=(20,5))
        ctk.CTkLabel(header_frame, text=f"{len(self.produtos_temp)} produtos encontrados. Selecione os que deseja salvar.", text_color=CORES["text_gray"]).pack(pady=(0, 20))

        # Barra Ferramentas
        toolbar = ctk.CTkFrame(popup, fg_color=CORES["bg_card"], height=50, corner_radius=0)
        toolbar.pack(fill="x", pady=(0, 10))

        def marcar_todos(estado):
            for item in self.check_vars:
                item["var"].set(estado)

        ctk.CTkButton(toolbar, text="MARCAR TODOS", command=lambda: marcar_todos(1),
                                   fg_color=CORES["bg_menu"], hover_color=CORES["accent_red"], width=150, font=("Roboto", 12, "bold")).pack(side="left", padx=(20, 10), pady=10)

        ctk.CTkButton(toolbar, text="DESMARCAR TODOS", command=lambda: marcar_todos(0),
                                      fg_color=CORES["bg_menu"], hover_color=CORES["bg_root"], width=150, font=("Roboto", 12, "bold"), text_color=CORES["text_gray"]).pack(side="left", padx=10, pady=10)

        # Lista
        scroll = ctk.CTkScrollableFrame(popup, width=800, height=450, fg_color="transparent", scrollbar_button_color=CORES["accent_red"])
        scroll.pack(pady=5, padx=20, fill="both", expand=True)

        self.check_vars = []
        
        for p in self.produtos_temp:
            frame_item = ctk.CTkFrame(scroll, fg_color=CORES["bg_card"], border_width=1, border_color=CORES["borda"], corner_radius=10)
            frame_item.pack(fill="x", pady=5)
            
            var = ctk.IntVar(value=0)
            
            chk = ctk.CTkCheckBox(frame_item, text="", variable=var, width=24, height=24, checkbox_width=24, checkbox_height=24, 
                                  border_width=2, fg_color=CORES["accent_red"], hover_color=CORES["accent_hover"], border_color=CORES["text_gray"])
            chk.pack(side="left", padx=20, pady=15)
            
            info_frame = ctk.CTkFrame(frame_item, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, pady=10)
            
            ctk.CTkLabel(info_frame, text=p['nome'], font=("Roboto", 13, "bold"), anchor="w", text_color=CORES["text_white"], wraplength=650).pack(fill="x")
            
            cor_preco = CORES["accent_red"] if "R$" in p['preco'] else CORES["text_gray"]
            ctk.CTkLabel(info_frame, text=p['preco'], font=("Roboto", 14, "bold"), anchor="w", text_color=cor_preco).pack(fill="x", pady=(5,0))
            
            self.check_vars.append({"dados": p, "var": var})

        def salvar_final():
            final = [item["dados"] for item in self.check_vars if item["var"].get() == 1]
            if not final: return
            
            nome = f"coleta_{self.termo_usado.replace(' ', '_')}.json"
            try:
                with open(nome, 'w', encoding='utf-8') as f:
                    json.dump(final, f, indent=4, ensure_ascii=False)
                
                # Usa a mesma função de fechar para garantir o destravamento
                self.escrever_log(self.log_coleta, f"Sucesso! Arquivo salvo: {nome} ({len(final)} itens)")
                ao_fechar() 

            except Exception as e:
                print(e)

        rodape = ctk.CTkFrame(popup, fg_color=CORES["bg_menu"], height=80, corner_radius=0)
        rodape.pack(fill="x", side="bottom")
        ctk.CTkButton(rodape, text="SALVAR SELECIONADOS (.JSON)", command=salvar_final, 
                      fg_color=CORES["accent_red"], hover_color=CORES["accent_hover"], height=50, 
                      font=("Montserrat", 15, "bold"), corner_radius=10).pack(fill="x", padx=30, pady=15)

    # ================= UPDATE =================
    def thread_update(self):
        threading.Thread(target=self.rodar_update).start()

    def selecionar_json_update(self):
        caminho = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if caminho:
            self.arquivo_para_atualizar = caminho
            self.lbl_arquivo_selecionado.configure(text=os.path.basename(caminho), text_color=CORES["accent_red"], font=("Roboto", 12, "bold"))
            self.btn_iniciar_update.configure(state="normal", fg_color=CORES["accent_red"])
            self.escrever_log(self.log_update, f"Arquivo carregado: {os.path.basename(caminho)}")

    def rodar_update(self):
        try:
            with open(self.arquivo_para_atualizar, 'r', encoding='utf-8') as f:
                dados = json.load(f)
            
            if not dados: return

            self.btn_iniciar_update.configure(state="disabled", text="PROCESSANDO...", fg_color=CORES["bg_card"])
            self.escrever_log(self.log_update, f"Iniciando atualização de {len(dados)} produtos...", limpar=True)
            
            driver = self.get_driver()
            atualizados = []
            
            for i, produto in enumerate(dados):
                try:
                    self.escrever_log(self.log_update, f"[{i+1}/{len(dados)}] Checando: {produto['nome'][:40]}...")
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
                    
                except Exception as e:
                    self.escrever_log(self.log_update, f"Erro item {i}: {e}")
                    atualizados.append(produto)
            
            nome_novo = self.arquivo_para_atualizar.replace(".json", "_atualizado.json")
            with open(nome_novo, 'w', encoding='utf-8') as f:
                json.dump(atualizados, f, indent=4, ensure_ascii=False)
            
            self.escrever_log(self.log_update, "Atualização Completa!")
            self.escrever_log(self.log_update, f"Arquivo salvo: {nome_novo}")

        except Exception as e:
            self.escrever_log(self.log_update, f"Erro fatal: {e}")
        finally:
            if 'driver' in locals() and driver: driver.quit()
            self.btn_iniciar_update.configure(state="normal", text="ATUALIZAR AGORA", fg_color=CORES["accent_red"])

    # ================= UNIR =================
    def executar_uniao(self):
        arquivos = filedialog.askopenfilenames(filetypes=[("JSON files", "*.json")])
        if not arquivos: return

        self.escrever_log(self.log_unir, f"Processando {len(arquivos)} arquivos...", limpar=True)
        
        mega_lista = []
        ids_existentes = set()
        total_lidos = 0
        
        for arq in arquivos:
            try:
                with open(arq, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    total_lidos += len(dados)
                    
                    for item in dados:
                        chave = item.get('id', item.get('link'))
                        if chave not in ids_existentes:
                            mega_lista.append(item)
                            ids_existentes.add(chave)
            except Exception as e:
                self.escrever_log(self.log_unir, f"Erro ao ler {arq}: {e}")

        nome_final = f"banco_unificado_{int(time.time())}.json"
        try:
            with open(nome_final, 'w', encoding='utf-8') as f:
                json.dump(mega_lista, f, indent=4, ensure_ascii=False)
            
            self.escrever_log(self.log_unir, "="*30)
            self.escrever_log(self.log_unir, f"Lidos: {total_lidos} produtos")
            self.escrever_log(self.log_unir, f"Salvos: {len(mega_lista)} produtos únicos")
            self.escrever_log(self.log_unir, f"Arquivo gerado: {nome_final}")
            
        except Exception as e:
            self.escrever_log(self.log_unir, f"Erro ao salvar: {e}")

if __name__ == "__main__":
    app = AppBDDinamico()
    app.mainloop()
