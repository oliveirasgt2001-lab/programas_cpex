import tkinter as tk
from tkinter import messagebox, filedialog
import os
import confere_IR_SIPPES_DED_MIN_motor as motor

# ===================== VARIÁVEIS =====================
arq_cadastro = None
arq_financeiro = None
arq_tabpag = None
dir_saida = None

# ===================== FUNÇÕES =====================

def selecionar_cadastro():
    global arq_cadastro
    arq_cadastro = filedialog.askopenfilename(title="Selecione o arquivo de Cadastro")
    lbl_cadastro.config(text=arq_cadastro or "Nenhum arquivo selecionado")

def selecionar_financeiro():
    global arq_financeiro
    arq_financeiro = filedialog.askopenfilename(title="Selecione o arquivo Financeiro")
    lbl_financeiro.config(text=arq_financeiro or "Nenhum arquivo selecionado")

def selecionar_tabpag():
    global arq_tabpag
    arq_tabpag = filedialog.askopenfilename(title="Selecione o arquivo TAB PAG")
    lbl_tabpag.config(text=arq_tabpag or "Nenhum arquivo selecionado")

def selecionar_saida():
    global dir_saida
    dir_saida = filedialog.askdirectory(title="Selecione o diretório de saída")
    lbl_saida.config(text=dir_saida or "Diretório padrão")

def validar_arquivos():
    global dir_saida

    if not arq_cadastro or not arq_financeiro or not arq_tabpag:
        messagebox.showwarning("Atenção", "Selecione todos os arquivos antes de executar.")
        return False

    # Se não escolher diretório de saída, usa o mesmo do cadastro
    if not dir_saida:
        dir_saida = os.path.dirname(arq_cadastro)

    motor.configurar_arquivos(arq_cadastro, arq_financeiro, arq_tabpag, dir_saida)
    return True

def executar_relatorio():
    if not validar_arquivos():
        return
    try:
        motor.processar()
        messagebox.showinfo("Sucesso", "Relatório de divergentes gerado com sucesso.")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def executar_debug_todos():
    if not validar_arquivos():
        return
    try:
        pessoas = motor.carregar_cadastro()
        motor.carregar_tabpag()
        motor.carregar_financeiro(pessoas)
        motor.gerar_debug_todos_txt(pessoas)
        messagebox.showinfo("Sucesso", "DEBUG de todos gerado com sucesso.")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

def executar_debug_individual():
    if not validar_arquivos():
        return
    valor = entrada.get().strip()
    if not valor:
        messagebox.showwarning("Atenção", "Informe o CP ou Identidade.")
        return
    try:
        pessoas = motor.carregar_cadastro()
        motor.carregar_tabpag()
        motor.carregar_financeiro(pessoas)
        motor.gerar_debug_pessoa_txt(pessoas, cp=valor, identidade=valor)
        messagebox.showinfo("Sucesso", "DEBUG individual gerado com sucesso.")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

# ===================== TELA =====================

janela = tk.Tk()
janela.title("Conferência IRRF")
janela.geometry("600x480")

tk.Label(janela, text="Sistema de Conferência IRRF", font=("Arial", 12, "bold")).pack(pady=10)

# ==== Seleção de arquivos ====

tk.Button(janela, text="Selecionar Cadastro", command=selecionar_cadastro).pack()
lbl_cadastro = tk.Label(janela, text="Nenhum arquivo selecionado", wraplength=550)
lbl_cadastro.pack()

tk.Button(janela, text="Selecionar Financeiro", command=selecionar_financeiro).pack()
lbl_financeiro = tk.Label(janela, text="Nenhum arquivo selecionado", wraplength=550)
lbl_financeiro.pack()

tk.Button(janela, text="Selecionar Rubricas", command=selecionar_tabpag).pack()
lbl_tabpag = tk.Label(janela, text="Nenhum arquivo selecionado", wraplength=550)
lbl_tabpag.pack()

tk.Button(janela, text="Selecionar Diretório de Saída", command=selecionar_saida).pack()
lbl_saida = tk.Label(janela, text="Diretório padrão", wraplength=550)
lbl_saida.pack()

tk.Label(janela, text="").pack(pady=5)

# ==== Funções ====

tk.Button(janela, text="Gerar Relatório Divergentes", width=30, command=executar_relatorio).pack(pady=5)
tk.Button(janela, text="DEBUG Todos", width=30, command=executar_debug_todos).pack(pady=5)

tk.Label(janela, text="CP ou Identidade para DEBUG individual:").pack(pady=5)
entrada = tk.Entry(janela, width=30)
entrada.pack(pady=5)

tk.Button(janela, text="DEBUG Individual", width=30, command=executar_debug_individual).pack(pady=5)

janela.mainloop()


