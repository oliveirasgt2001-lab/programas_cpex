import os
from datetime import datetime
import calendar

def normalizar_texto(txt):
    if not txt:
        return txt
    return txt.strip()

# =========================================================
# CAMINHOS
# =========================================================
ARQ_CADASTRO = None
ARQ_FINANCEIRO = None
ARQ_TABPAG = None
DIR_SAIDA = None

# =========================================================
# CONSTANTES
# =========================================================
VALOR_DEPENDENTE = 189.59
ISENCAO_IDOSO = 1903.98
FAIXA_ISENCAO = 2428.80
ALIQUOTA_PISO = 0.25
DEDUCAO_MINIMA_VALOR = FAIXA_ISENCAO * ALIQUOTA_PISO  # 607,20
RUBRICAS_COMPARACAO_MINIMO = {
"ND0001", "ND0011","ND0042","AD0001",  # FUSEX
"ND0002","ND0005", "ND0011", "FD0002", "FD0005", "FD0075" , "AD0039", "FD0039", "ND0040", "ND0039","ND0041","AD0002","AD0005",  # Pensão Militar
"FD0014","ND0014", "ND0035", "ND0036"  # Pensão Judicial
}
# =========================================================
# TABPAG (GLOBAL)
# =========================================================
TABPAG = {}

# =========================================================
# RUBRICAS A IGNORAR NOS CÁLCULOS
# =========================================================
RUBRICAS_IGNORAR = ["AR0084", "NR0084", "FR0085","FR0084", "ND0096", "AD0096", "DR0085", "NR0070", "DR0084", "AD0097", "FD0097", "DR0070", "AR0070", "FD0096", ]

# =========================================================
# TABPAG - POSICIONAL
# =========================================================
def carregar_tabpag():
    TABPAG.clear()
    with open(ARQ_TABPAG, encoding="utf-8") as f:
        next(f)
        for linha in f:
            rubrica = linha[1:7].strip().upper()
            tipo = linha[10:11].strip()
            flag = linha[13:14].strip()
            nome = corrigir_texto_misto(linha[16:60])
            if rubrica and flag:
                TABPAG[rubrica] = {"tipo": tipo, "flag": flag, "nome": nome}

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def formatar(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_idade_mes_atual(data):
    try:
        data = data.strip().replace("\x00", "").replace("\n", "").replace("\r", "")

        #print("DEBUG DATA:", repr(data))  # deixe isso TEMPORARIAMENTE para testar

        dia, mes, ano = data.split("/")

        dia = int(dia)
        mes = int(mes)
        ano = int(ano)

        # Ajuste de século
        if ano >= 30:
            ano += 1900
        else:
            ano += 2000

        dt = datetime(ano, mes, dia)

        hoje = datetime.now()
        ultimo_dia = calendar.monthrange(hoje.year, hoje.month)[1]
        data_futura = datetime(hoje.year, hoje.month, ultimo_dia)

        idade = data_futura.year - dt.year
        if (dt.month, dt.day) > (data_futura.month, data_futura.day):
            idade -= 1

        return idade

    except Exception as e:
        print("ERRO AO CALCULAR IDADE:", repr(data), e)
        return 0


def deducao_dependentes(qtd):
    return qtd * VALOR_DEPENDENTE

def deducao_idade(idade):
    return ISENCAO_IDOSO if idade >= 65 else 0.0

def calcular_irrf(base):
    tabela = [
        (2428.80, 0.0, 0.0),
        (2826.65, 0.075, 182.16),
        (3751.05, 0.15, 394.16),
        (4664.68, 0.225, 675.49),
        (float("inf"), 0.275, 908.73)
    ]
    for limite, aliq, parc in tabela:
        if base <= limite:
            return max(base * aliq - parc, 0)
    return 0.0

def desconto_progressivo(rendimento):
    if rendimento <= 5000:
        return 312.89
    if rendimento <= 7350:
        return 978.62 - (0.133145 * rendimento)
    return 0.0

def nome_rubrica(rub):
    regra = TABPAG.get(rub)
    if regra and "nome" in regra:
        return regra["nome"]
    return "SEM DESCRIÇÃO"

# 🔧 AJUSTE AQUI: valor com largura fixa à direita
def formatar_linha(rub, val, largura=50):
    texto = f"{rub} - {nome_rubrica(rub)}"
    valor_fmt = formatar(val).rjust(15)  # largura fixa para valores
    return f" {texto.ljust(largura)} R$ {valor_fmt}\n"

def corrigir_texto_misto(txt):
    return txt.replace('"','').strip()

def aplicar_minimo_ir(valor, minimo=10.00):
    return 0.0 if valor < minimo else valor

def configurar_arquivos(cadastro, financeiro, tabpag, dir_saida=None):
    global ARQ_CADASTRO, ARQ_FINANCEIRO, ARQ_TABPAG, DIR_SAIDA

    ARQ_CADASTRO = cadastro
    ARQ_FINANCEIRO = financeiro
    ARQ_TABPAG = tabpag

    if dir_saida:
        DIR_SAIDA = dir_saida
    else:
        if not DIR_SAIDA:
            raise Exception("Diretório de saída não configurado. Use configurar_arquivos().")
# =========================================================
# CADASTRO - POSICIONAL
# =========================================================
def carregar_cadastro():
    pessoas = {}
    with open(ARQ_CADASTRO, encoding="utf-8") as f:
        next(f)
        for linha in f:
            cp = linha[19:28].strip()
            identidade = linha[6:16].strip()

            dep_txt = linha[32:33].strip()
            dependentes = int(dep_txt) if dep_txt.isdigit() else 0

            data_nasc = linha[38:46].strip()

            nome = normalizar_texto(linha[48:].replace('"',''))

            pessoas[cp] = {
                "cp": cp,
                "identidade": identidade,
                "nome": nome,
                "data_nasc": data_nasc,
                "dependentes": dependentes,
                "rendimentos": [],
                "deducoes": [],
                "ir_sistema": 0.0
            }

    return pessoas

# =========================================================
# FINANCEIRO - POSICIONAL
# =========================================================
def carregar_financeiro(pessoas):
    with open(ARQ_FINANCEIRO, encoding="utf-8-sig") as f:
        next(f)
        for linha in f:
            cp = linha[21:30].strip()
            
            pessoa = pessoas.get(cp)
            if pessoa is None:
                continue
            
            rubrica = linha[33:39].strip().upper()
            if len(rubrica) < 2 :
                continue
            try:
                valor = float(linha[42:52].replace(".", "").replace(",", "."))
            except:
                valor = 0.0

            # IR do sistema (ND0010 + ND0015)
            if rubrica in ["ND0010", "ND0015"]:
                pessoa["ir_sistema"] += valor
                continue

            if rubrica in RUBRICAS_IGNORAR:
                continue

            tipo_duplo = rubrica[:2]
            natureza = rubrica[1]

            if tipo_duplo == "DR":
                pessoa["deducoes"].append((rubrica, valor))
            elif tipo_duplo == "DD":
                pessoa["rendimentos"].append((rubrica, valor))
            elif natureza == "R":
                pessoa["rendimentos"].append((rubrica, valor))
            elif natureza == "D":
                pessoa["deducoes"].append((rubrica, valor))

# =========================================================
# PROCESSAMENTO / RELATÓRIO
# =========================================================
def processar():
    pessoas = carregar_cadastro()
    carregar_tabpag()
    carregar_financeiro(pessoas)

    total_analisados = 0
    total_divergentes = 0
    total_sem_divergencia = 0

    nome_saida = f"resultado_ir_divergentes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    caminho_saida = os.path.join(DIR_SAIDA, nome_saida)

    with open(caminho_saida, "w", encoding="utf-8-sig") as out:
        out.write("RELATÓRIO IRRF – SOMENTE DIVERGENTES\n\n")

        for p in pessoas.values():
            total_analisados += 1
            idade = calcular_idade_mes_atual(p["data_nasc"])

            soma_rend = 0.0
           
            rend_validos = []
            ded_validas = []

            tabpag = TABPAG  # cache local (mais rápido)

            for rub, val in p["rendimentos"]:
                regra = tabpag.get(rub)
                if regra and regra["flag"] == "1":
                    soma_rend += val
                    rend_validos.append((rub, val))
            
            for rub, val in p["deducoes"]:
                regra = TABPAG.get(rub)
                if regra and regra["flag"] in ["2", "4"]:
                    ded_validas.append((rub, val))

            ded_dep = deducao_dependentes(p["dependentes"])
            ded_idade = deducao_idade(idade)

            deducoes_comparacao = ded_dep + ded_idade
            outras_deducoes = 0.0

            for rub, val in ded_validas:

                if rub in RUBRICAS_COMPARACAO_MINIMO:
                    deducoes_comparacao += val
                else:
                    outras_deducoes += val

            if deducoes_comparacao <= DEDUCAO_MINIMA_VALOR:
                deducao_base = DEDUCAO_MINIMA_VALOR
                tipo_deducao = "MÍNIMA"
            else:
                deducao_base = deducoes_comparacao
                tipo_deducao = "REAL"

            ded_aplicada = deducao_base + outras_deducoes
            base = soma_rend - ded_aplicada
            ir_bruto = calcular_irrf(base)
            desconto_lei = desconto_progressivo(soma_rend)
            ir_final = aplicar_minimo_ir(max(ir_bruto - desconto_lei, 0))

            if abs(ir_final - p["ir_sistema"]) <= 0.10:
                total_sem_divergencia += 1
                print(
                p["cp"],
                "IR_CALC:", ir_final,
                "IR_SIST:", p["ir_sistema"]
)
                continue

            total_divergentes += 1

            out.write("-" * 70 + "\n")
            out.write(f"CP: {p['cp']}\n")
            out.write(f"Identidade: {p['identidade']}\n")
            out.write(f"Nome: {p['nome']}\n")
            out.write(f"Idade: {idade}\n")
            out.write(f"Dependentes: {p['dependentes']}\n\n")

            out.write("RENDIMENTOS CONSIDERADOS:\n")
            for rub, val in rend_validos:
                out.write(formatar_linha(rub, val))
            out.write(f"TOTAL RENDIMENTOS: R$ {formatar(soma_rend)}\n\n")

            out.write("DEDUÇÕES CONSIDERADAS:\n")
            for rub, val in ded_validas:
                out.write(formatar_linha(rub, val))

            out.write(f"\nDedução por dependentes: R$ {formatar(deducao_dependentes(p['dependentes']))}\n")
            out.write(f"Dedução por idade: R$ {formatar(deducao_idade(idade))}\n")
            out.write(f"Dedução base: R$ {formatar(deducao_base)} ({tipo_deducao})\n")
            out.write(f"Outras deduções: R$ {formatar(outras_deducoes)}\n")
            out.write(f"TOTAL DEDUÇÃO APLICADA: R$ {formatar(ded_aplicada)}\n\n")

            out.write("DESCONTO LEI 15.270:\n")
            out.write(f"  Aplicado: {'SIM' if desconto_lei > 0 else 'NÃO'}\n")
            out.write(f"  Valor: R$ {formatar(desconto_lei)}\n\n")

            out.write(f"Base de cálculo: R$ {formatar(base)}\n")
            out.write(f"IR Calculado: R$ {formatar(ir_final)}\n")
            out.write(f"IR Sistema (ND0010+ND0015): R$ {formatar(p['ir_sistema'])}\n")
            out.write(f"DIFERENÇA: R$ {formatar(ir_final - p['ir_sistema'])}\n")
            out.write("-" * 70 + "\n\n")

        out.write("\nRESUMO DA CONFERÊNCIA\n")
        out.write("-" * 40 + "\n")
        out.write(f"TOTAL ANALISADOS: {total_analisados}\n")
        out.write(f"SEM DIVERGÊNCIA: {total_sem_divergencia}\n")
        out.write(f"COM DIVERGÊNCIA: {total_divergentes}\n")

    print("Arquivo gerado em:", caminho_saida)

# =========================================================
# FUNÇÃO AUXILIAR PARA DEBUG COMPLETO (NOVA)
# =========================================================
def gerar_relatorio_completo_pessoa(out, p):
    idade = calcular_idade_mes_atual(p["data_nasc"])

    soma_rend = 0.0
    soma_ded = 0.0
    rend_validos = []
    ded_validas = []

    for rub, val in p["rendimentos"]:
        regra = TABPAG.get(rub)
        if regra and regra["flag"] == "1":
            soma_rend += val
            rend_validos.append((rub, val))

    for rub, val in p["deducoes"]:
        regra = TABPAG.get(rub)
        if regra and regra["flag"] in ("2", "4"):
            ded_validas.append((rub, val))
        
    ded_dep = deducao_dependentes(p["dependentes"])
    ded_idade = deducao_idade(idade)

    deducoes_comparacao = ded_dep + ded_idade
    outras_deducoes = 0.0

    for rub, val in ded_validas:
        if rub in RUBRICAS_COMPARACAO_MINIMO:
            deducoes_comparacao += val
        else:
            outras_deducoes += val

    if deducoes_comparacao <= DEDUCAO_MINIMA_VALOR:
        deducao_base = DEDUCAO_MINIMA_VALOR
        tipo_deducao = "MÍNIMA"
    else:
        deducao_base = deducoes_comparacao
        tipo_deducao = "REAL"

    ded_aplicada = deducao_base + outras_deducoes

    base = soma_rend - ded_aplicada 
    ir_bruto = calcular_irrf(base)
    desconto_lei = desconto_progressivo(soma_rend)
    ir_final = aplicar_minimo_ir(max(ir_bruto - desconto_lei, 0))

    out.write("-" * 70 + "\n")
    out.write(f"CP: {p['cp']}\n")
    out.write(f"Identidade: {p['identidade']}\n")
    out.write(f"Nome: {p['nome']}\n")
    out.write(f"Idade: {idade}\n")
    out.write(f"Dependentes: {p['dependentes']}\n\n")

    out.write("RENDIMENTOS CONSIDERADOS:\n")
    for rub, val in rend_validos:
        out.write(formatar_linha(rub, val))
    out.write(f"TOTAL RENDIMENTOS: R$ {formatar(soma_rend)}\n\n")

    out.write("DEDUÇÕES CONSIDERADAS:\n")
    for rub, val in ded_validas:
        out.write(formatar_linha(rub, val))

    out.write(f"\nDedução por dependentes: R$ {formatar(deducao_dependentes(p['dependentes']))}\n")
    out.write(f"Dedução por idade: R$ {formatar(deducao_idade(idade))}\n")
    out.write(f"TOTAL DEDUÇÃO APLICADA: R$ {formatar(ded_aplicada)} ({tipo_deducao})\n\n")

    out.write("DESCONTO LEI 15.270:\n")
    out.write(f"  Aplicado: {'SIM' if desconto_lei > 0 else 'NÃO'}\n")
    out.write(f"  Valor: R$ {formatar(desconto_lei)}\n\n")

    out.write(f"Base de cálculo: R$ {formatar(base)}\n")
    out.write(f"IR Calculado: R$ {formatar(ir_final)}\n")
    out.write(f"IR Sistema (ND0010+ND0015): R$ {formatar(p['ir_sistema'])}\n")
    out.write(f"DIFERENÇA: R$ {formatar(ir_final - p['ir_sistema'])}\n")
    out.write("-" * 70 + "\n\n")

# =========================================================
# DEBUGS NOVOS (ADICIONADOS)
# =========================================================
def localizar_pessoa(pessoas, cp=None, identidade=None):
    tabpag = TABPAG

    for p in pessoas.values():
        if cp and p["cp"] == cp:
            return p
        if identidade and p["identidade"] == identidade:
            return p
    return None

def gerar_debug_pessoa_txt(pessoas, cp=None, identidade=None):
    p = localizar_pessoa(pessoas, cp, identidade)
    if not p:
        print("Pessoa não encontrada.")
        return

    nome_saida = f"debug_ir_{p['cp']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    caminho_saida = os.path.join(DIR_SAIDA, nome_saida)

    with open(caminho_saida, "w", encoding="utf-8-sig") as out:
        gerar_relatorio_completo_pessoa(out, p)

    print("Arquivo de DEBUG individual gerado em:", caminho_saida)

def gerar_debug_todos_txt(pessoas):
    nome_saida = f"debug_ir_todos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    caminho_saida = os.path.join(DIR_SAIDA, nome_saida)
    with open(caminho_saida, "w", encoding="utf-8-sig") as out:
        out.write("DEBUG COMPLETO - TODOS OS CÁLCULOS DE IR\n\n")
        for p in pessoas.values():
            gerar_relatorio_completo_pessoa(out, p)

    print("Arquivo de DEBUG geral gerado em:", caminho_saida)

# =========================================================
# EXECUÇÃO
# =========================================================
if __name__ == "__main__":
    print("Este arquivo é o MOTOR do sistema. Use pela GUI confere_IR_GUI.py")
    pessoas = carregar_cadastro()
    carregar_tabpag()
    carregar_financeiro(pessoas)

    print("\nOPÇÕES:")
    print("0 → Relatório normal (divergentes)")
    print("1 → DEBUG de todos")
    print("CP ou Identidade → DEBUG individual")

    opcao = input(">> ").strip()

    if opcao == "0":
        processar()
    elif opcao == "1":
        gerar_debug_todos_txt(pessoas)
    else:
        gerar_debug_pessoa_txt(pessoas, cp=opcao, identidade=opcao)
