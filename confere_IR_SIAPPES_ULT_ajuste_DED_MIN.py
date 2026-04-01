import os
from datetime import datetime
import calendar
import tkinter as tk
from tkinter import filedialog, messagebox

# =========================================================
# CONFIGURAÇÕES DE POSIÇÃO
# =========================================================
TIPO_ARQUIVO = None
CPF_INI = None
CPF_FIM = None

def configurar_layout_cadastro(nome_arquivo):
    global NOME_INI, NOME_FIM
    global DATA_NASC_INI, DATA_NASC_FIM
    global DEPENDENTES_INI, DEPENDENTES_FIM
    global CALC_INI, CALC_FIM
    global TIPO_ARQUIVO
    global CPF_INI, CPF_FIM

    nome_arquivo = nome_arquivo.upper()

    if ".MI." in nome_arquivo:
        TIPO_ARQUIVO = "MI"
        DATA_NASC_INI = 99
        DATA_NASC_FIM = 107
        DEPENDENTES_INI = 100
        DEPENDENTES_FIM = 102
        NOME_INI = 24
        NOME_FIM = 64
        CALC_INI = 95
        CALC_FIM = 96
        CPF_INI = 84
        CPF_FIM = 95

    elif ".PE." in nome_arquivo:
        TIPO_ARQUIVO = "PE"
        DATA_NASC_INI = 49
        DATA_NASC_FIM = 57
        DEPENDENTES_INI = 25
        DEPENDENTES_FIM = 27
        NOME_INI = 57
        NOME_FIM = 104
        CALC_INI = 35
        CALC_FIM = 36
        CPF_INI = 36
        CPF_FIM = 47

    elif ".MA" in nome_arquivo:
        TIPO_ARQUIVO = "MA"
        DATA_NASC_INI = 100
        DATA_NASC_FIM = 108
        DEPENDENTES_INI = 100
        DEPENDENTES_FIM = 102
        NOME_INI = 24
        NOME_FIM = 72
        CALC_INI = None
        CALC_FIM = None
        CPF_INI = 84
        CPF_FIM = 95

CP_CAD_INI = 8
CP_CAD_FIM = 15
PREC_INI = 5
PREC_FIM = 7
CP_FIN_INI = 8
CP_FIN_FIM = 15
RUBRICA_INI = 24
RUBRICA_FIM = 80

# =========================================================
# RUBRICAS
# =========================================================
RUBRICAS_TRIBUTAVEIS = set()
RUBRICAS_EXCLUIDAS_RENDIMENTO = {"A85","A86","A84","C86","C87","C84","B84","B85","B86","B87","A87"}
EXCLUIR_DEDUCAO = {"I85", "I86", "H92","H90"}
# rubricas que entram na comparação com a dedução mínima
RUBRICAS_COMPARACAO_MINIMO = {"Z01", "Z02" , "Z05", "Z11", "Z12", "ZKA", "ZKB", "Z99", "ZJA","ZM5", "ZM7", "ZK6"}  # exemplo: Pensão Militar e FUSEX
# =========================================================
# CONSTANTES
# =========================================================
VALOR_DEPENDENTE = 189.59
ISENCAO_IDOSO = 1903.98
FAIXA_ISENCAO = 2428.80
ALIQUOTA_PISO = 0.25

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def formatar_brasil(valor):
    texto = f"{valor:,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")

def extrair_valor_rubrica(trecho):
    try:
        return int(trecho[5:13]) / 100
    except:
        return 0.0

def extrair_inteiro_seguro(trecho):
    trecho = trecho.strip()
    return int(trecho) if trecho.isdigit() else 0

def calcular_idade(data_nasc):
    try:
        dt = datetime.strptime(data_nasc.strip(), "%d%m%Y")
        hoje = datetime.now()
        return hoje.year - dt.year - ((hoje.month, hoje.day) < (dt.month, dt.day))
    except:
        return 0

def calcular_idade_mes_atual(data_nasc):
    try:
        dt = datetime.strptime(data_nasc.strip(), "%d%m%Y")
        hoje = datetime.now()
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_futura = datetime(hoje.year, hoje.month, ultimo_dia)
        return data_futura.year - dt.year - ((data_futura.month, data_futura.day) < (dt.month, dt.day))
    except:
        return 0

# =========================================================
# IRRF
# =========================================================
def calcular_irrf(base_calculo):
    aliquotas = [
        (2428.80, 0.0, 0.0),
        (2826.65, 0.075, 182.16),
        (3751.05, 0.15, 394.16),
        (4664.68, 0.225, 675.49),
        (float("inf"), 0.275, 908.73)
    ]

    if base_calculo <= 0:
        return 0.0

    for limite, aliquota, parcela in aliquotas:
        if base_calculo <= limite:
            return round(max(base_calculo * aliquota - parcela, 0), 2)

    return 0.0

def desconto_progressivo(rendimento_total):
    if rendimento_total <= 5000.00:
        return 312.89
    if 5000.01 <= rendimento_total <= 7350.00:
        return 978.62 - (0.133145 * rendimento_total)
    return 0.0

def deducao_dependentes(qtd):
    return qtd * VALOR_DEPENDENTE

def deducao_idade(idade):
    return ISENCAO_IDOSO if idade >= 65 else 0.0

def deducao_minima():
    return FAIXA_ISENCAO * ALIQUOTA_PISO

# =========================================================
# CADASTRO
# =========================================================
def carregar_cadastro(caminho):
    pessoas = {}
    chave_atual = None

    with open(caminho, encoding="latin-1") as f:
        for linha in f:
            tipo = linha[0]

            if tipo == "1":
                indice = "0" if TIPO_ARQUIVO == "MA" else linha[CALC_INI:CALC_FIM].strip().upper()

                if indice in ("3", "C", "6", "1","7","F"):
                    chave_atual = None
                    continue

                prec = linha[PREC_INI:PREC_FIM].strip()
                cp = linha[CP_CAD_INI:CP_CAD_FIM].strip()
                chave_atual = f"{prec}{cp}"

                pessoas[chave_atual] = {
                    "prec": prec,
                    "cp": cp,
                    "cpf": linha[CPF_INI:CPF_FIM].strip() if CPF_INI is not None else "",
                    "nome": linha[NOME_INI:NOME_FIM].strip(),
                    "data_nasc": linha[DATA_NASC_INI:DATA_NASC_FIM],
                    "dependentes": 0,
                    "rendimentos": 0.0,
                    "deducoes": 0.0,
                    "ir_sistema": 0.0,
                    "rubricas_rendimento": {},
                    "rubricas_deducao": {},
                    "calc": indice
                }

            elif tipo == "2" and chave_atual in pessoas:
                pessoas[chave_atual]["dependentes"] = extrair_inteiro_seguro(
                    linha[DEPENDENTES_INI:DEPENDENTES_FIM]
                )

    return pessoas

# =========================================================
# FINANCEIRO (COM TIPO 5 - Z99 / ZJA)
# =========================================================
def carregar_financeiro(caminho, pessoas):
    with open(caminho, encoding="latin-1") as f:
        for linha in f:
            tipo = linha[0]
            if tipo not in ("3", "4", "5"):
                continue

            prec = linha[PREC_INI:PREC_FIM].strip()
            cp = linha[CP_FIN_INI:CP_FIN_FIM].strip()
            chave = f"{prec}{cp}"

            if chave not in pessoas:
                continue

            if tipo in ("3", "4"):
                rubrica = linha[RUBRICA_INI:RUBRICA_INI + 3].strip().upper()
                valor = extrair_valor_rubrica(linha[RUBRICA_INI:RUBRICA_FIM])

                if tipo == "3" and rubrica in RUBRICAS_TRIBUTAVEIS and rubrica not in RUBRICAS_EXCLUIDAS_RENDIMENTO:
                    pessoas[chave]["rendimentos"] += valor
                    pessoas[chave]["rubricas_rendimento"][rubrica] = (
                        pessoas[chave]["rubricas_rendimento"].get(rubrica, 0) + valor
                    )

                elif tipo == "4" and rubrica in RUBRICAS_TRIBUTAVEIS and rubrica not in EXCLUIR_DEDUCAO:
                    pessoas[chave]["deducoes"] += valor
                    pessoas[chave]["rubricas_deducao"][rubrica] = (
                        pessoas[chave]["rubricas_deducao"].get(rubrica, 0) + valor
                    )

                elif tipo == "4" and (rubrica == "Z10" or rubrica == "Z09"):
                    pessoas[chave]["ir_sistema"] += valor

            elif tipo == "5":
                rubrica = linha[23:26].strip().upper()
                try:
                    valor = int(linha[28:36]) / 100
                except:
                    valor = 0.0

                if rubrica in ("Z99", "ZJA") and rubrica in RUBRICAS_TRIBUTAVEIS:
                    pessoas[chave]["deducoes"] += valor
                    pessoas[chave]["rubricas_deducao"][rubrica] = (
                        pessoas[chave]["rubricas_deducao"].get(rubrica, 0) + valor
                    )

# =========================================================
# TABPAG
# =========================================================
def carregar_TABPAG(caminho):
    rubricas_validas = set()
    with open(caminho, encoding="latin-1") as f:
        for linha in f:
            if linha[12:13] != "7":
                continue
            rubrica = linha[19:22].strip().upper()
            if linha[59:60] == "1" and rubrica:
                rubricas_validas.add(rubrica)
    return rubricas_validas

# =========================================================
# PROCESSAMENTO (SEU MAIN ORIGINAL)
# =========================================================
def processar(caminho_cadastro, caminho_financeiro, caminho_tabpag):
    configurar_layout_cadastro(os.path.basename(caminho_cadastro))

    pessoas = carregar_cadastro(caminho_cadastro)
    RUBRICAS_TRIBUTAVEIS.clear()
    RUBRICAS_TRIBUTAVEIS.update(carregar_TABPAG(caminho_tabpag))

    carregar_financeiro(caminho_financeiro, pessoas)

    # # ================= DEBUG =================
    # print("\nDEBUG FINAL ANTES DO RELATÓRIO")
    # for cp, dados in pessoas.items():
    #     print(cp, dados)
    # # =========================================

    nome_saida = f"resultado_ir_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    nome_saida_div = f"divergentes_ir_2026_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    divergentes = []
    soma_diferencas = 0.0
    soma_maior = 0.0
    soma_menor = 0.0    

    with open(nome_saida, "w", encoding="utf-8") as out:
        out.write("RESULTADO IRRF 2026\n\n")
        valor_deducao_minima = deducao_minima()
        for cp, dados in pessoas.items():
            idade = calcular_idade(dados["data_nasc"])
            idade_para_deducao = calcular_idade_mes_atual(dados["data_nasc"])

            ded_dep = deducao_dependentes(dados["dependentes"])
            ded_idade = deducao_idade(idade_para_deducao)

            if ded_dep > 0:
                dados["rubricas_deducao"]["DEP"] = ded_dep
            if ded_idade > 0:
                dados["rubricas_deducao"]["IDOSO"] = ded_idade

# =========================================================
# Separação das deduções para cálculo da dedução mínima
# =========================================================
# deduções que entram na comparação com o mínimo
            deducoes_comparacao = ded_dep + ded_idade

# deduções adicionais (não entram na comparação)
            outras_deducoes = 0.0

            for r, v in dados["rubricas_deducao"].items():

                if r in RUBRICAS_COMPARACAO_MINIMO:
                    deducoes_comparacao += v

                elif r not in ("DEP", "IDOSO"):  # evita duplicar dependente e idade
                    outras_deducoes += v


# aplica regra da dedução mínima
            deducao_base = max(deducoes_comparacao, valor_deducao_minima)

# dedução total aplicada    
            deducao_aplicada = deducao_base + outras_deducoes   

            base_ir = dados["rendimentos"] - deducao_aplicada   

            irrf_bruto = calcular_irrf(base_ir)
            desconto_lei = desconto_progressivo(dados["rendimentos"])
            irrf = max(irrf_bruto - desconto_lei, 0.0)

            if irrf < 9.99:
                irrf = 0.0

            diferenca = irrf - dados["ir_sistema"]
            if diferenca > 0:
                soma_maior += diferenca
            elif diferenca < 0:
                soma_menor += diferenca
            divergente = abs(diferenca) > 0.10

            if divergente:
                divergentes.append((cp, dados, irrf, diferenca, desconto_lei))

            out.write("-" * 60 + "\n")
            out.write(f"PREC/CP: {dados['prec']}{dados['cp']}\n")
            out.write(f"Nome: {dados['nome']} | Idade: {idade}| Calc: {dados['calc']} \n")
            out.write(f"CPF: {dados.get('cpf','')}\n")
            out.write(f"Rendimentos: R$ {formatar_brasil(dados['rendimentos'])}\n")

            out.write("Rubricas de Rendimento:\n")
            for r, v in dados["rubricas_rendimento"].items():
                out.write(f"  {r}: R$ {formatar_brasil(v)}\n")

            out.write("Rubricas de Dedução:\n")
            for r, v in dados["rubricas_deducao"].items():
                out.write(f"  {r}: R$ {formatar_brasil(v)}\n")

            tipo = "MÍNIMA" if deducao_base == deducao_minima() else "REAL"
            out.write(f"Dedução aplicada no cálculo ({tipo}): R$ {formatar_brasil(deducao_aplicada)}\n")
            out.write(f"Desconto da Lei 15.270/2025: R$ {formatar_brasil(desconto_lei)}\n")
            out.write(f"IR Calculado: R$ {formatar_brasil(irrf)}\n")
            out.write(f"IR Sistema (Z10 ou Z09): R$ {formatar_brasil(dados['ir_sistema'])}\n")

            if divergente:
                out.write("OBSERVAÇÃO: DIVERGÊNCIA IDENTIFICADA\n")

            out.write("-" * 60 + "\n\n")
        # =========================================================
        # RELATÓRIO SOMENTE DE DIVERGENTES
        # =========================================================
        total_divergentes = len(divergentes)

        out.write("\n\n")
        out.write("=" * 60 + "\n")
        out.write("RELATÓRIO SOMENTE DE DIVERGENTES\n")
        out.write(f"TOTAL DE DIVERGENTES: {total_divergentes}\n")
        out.write(f"SOMA TOTAL DAS DIFERENÇAS A RECOLHER (IR CALCULADO > IR SISTEMA): " f"R$ {formatar_brasil(soma_maior)}\n")
        out.write(f"SOMA TOTAL DAS DIFERENÇAS A DEVOLVER (IR CALCULADO < IR SISTEMA): " f"R$ {formatar_brasil(soma_menor)}\n")

        out.write("=" * 60 + "\n\n")

        if total_divergentes == 0:
            out.write("nenhuma divergência encontrada\n")
        else:
            for cp, dados, irrf, diferenca, desconto_lei in divergentes:
                idade = calcular_idade(dados["data_nasc"])
                idade_para_deducao = calcular_idade_mes_atual(dados["data_nasc"])
                ded_dep = deducao_dependentes(dados["dependentes"])
                ded_idade = deducao_idade(idade_para_deducao)
                deducoes_comparacao = ded_dep + ded_idade
                outras_deducoes = 0.0

                for r, v in dados["rubricas_deducao"].items():

                    if r in RUBRICAS_COMPARACAO_MINIMO:
                        deducoes_comparacao += v

                    elif r not in ("DEP", "IDOSO"):
                        outras_deducoes += v

                deducao_base = max(deducoes_comparacao, valor_deducao_minima)
                deducao_aplicada = deducao_base + outras_deducoes
                
                
                
                tipo = "MÍNIMA" if deducao_base == deducao_minima() else "REAL"
                
                situacao = "MAIOR" if diferenca > 0 else "MENOR"

                out.write("-" * 60 + "\n")
                out.write(f"PREC/CP: {dados['prec']}{dados['cp']}\n")
                out.write(f"Nome: {dados['nome']} | Idade: {idade}| Calc: {dados['calc']} \n")
                out.write(f"CPF: {dados.get('cpf','')}\n")
                out.write(f"Idade: {idade}\n")
                out.write(f"Dependentes: {dados['dependentes']}\n")
                out.write(f"Rendimentos: R$ {formatar_brasil(dados['rendimentos'])}\n")
                out.write("Rubricas de Rendimento:\n")
                for r, v in dados["rubricas_rendimento"].items():
                    out.write(f"  {r}: R$ {formatar_brasil(v)}\n")
                out.write("Rubricas de Dedução:\n")
                for r, v in dados["rubricas_deducao"].items():
                    out.write(f"  {r}: R$ {formatar_brasil(v)}\n")
                out.write(f"Dedução aplicada no cálculo ({tipo}): R$ {formatar_brasil(deducao_aplicada)}\n")
                out.write(f"Desconto da Lei 15.270/2025: R$ {formatar_brasil(desconto_lei)}\n")
                out.write(f"IR Calculado: R$ {formatar_brasil(irrf)}\n")
                out.write(f"IR Sistema (Z10 ou Z09): R$ {formatar_brasil(dados['ir_sistema'])}\n")
                out.write(
                    f"O IR DO SISTEMA (Z10 ou Z09), DE ACORDO COM OS CÁLCULOS, DEVERIA SER: "
                    f"R$ {formatar_brasil(abs(diferenca))} ({situacao})\n"
)

        out.write("-" * 60 + "\n\n")

    print(f"Arquivo gerado: {nome_saida}")
    os.startfile(nome_saida)
# =========================================================
# INTERFACE GRÁFICA
# =========================================================
def selecionar(var):
    caminho = filedialog.askopenfilename()
    if caminho:
        var.set(caminho)

def gerar():
    if not cadastro.get() or not financeiro.get() or not tabpag.get():
        messagebox.showwarning("Atenção", "Selecione todos os arquivos.")
        return

    try:
        btn_gerar.config(text="AGUARDE! PROCESSANDO...")

        root.update_idletasks()  # força atualização da interface

        processar(cadastro.get(), financeiro.get(), tabpag.get())

        messagebox.showinfo("Concluído", "Relatório gerado com sucesso!")
    finally:
        btn_gerar.config(text="GERAR RELATÓRIO")



root = tk.Tk()
root.title("Conferência IRRF 2026")
root.geometry("1100x260")
root.resizable(False, False)

cadastro = tk.StringVar()
financeiro = tk.StringVar()
tabpag = tk.StringVar()

def linha(texto, var, row):
    tk.Label(root, text=texto).grid(row=row, column=0, padx=15, pady=15, sticky="w")
    tk.Entry(root, textvariable=var, width=110).grid(row=row, column=1)
    tk.Button(root, text="...", command=lambda: selecionar(var)).grid(row=row, column=2)

linha("Arquivo CADASTRAL tipo: SCAT, SCAI ou SCAM:", cadastro, 0)
linha("Arquivo FINANCEIRO tipo SMOT, SMOI ou SMOM :", financeiro, 1)
linha("Arquivo TABPAG: tipo PPP070", tabpag, 2)

btn_gerar = tk.Button(root, text="GERAR RELATÓRIO", width=25, command=gerar)
btn_gerar.grid(row=4, column=1, pady=25)

root.mainloop()