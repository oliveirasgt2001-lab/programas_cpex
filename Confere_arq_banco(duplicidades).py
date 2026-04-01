import os
import sys
import re
from collections import defaultdict


def carregar_arquivo(caminho):
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as arq:
            return arq.readlines()
    except UnicodeDecodeError:
        with open(caminho, "r", encoding="latin-1", errors="ignore") as arq:
            return arq.readlines()


def encontrar_caracteres_especiais_com_pos(linha):
    especiais = []
    for i, c in enumerate(linha):
        pos = i + 1
        if c in ['\n', '\r', '\t']:
            continue
        if c == '.' and pos == 240:
            continue
        if not re.match(r"[A-Za-z0-9 \-']", c):
            especiais.append((pos, c))
    return especiais


def verificar_caracteres_especiais_em_todas_linhas(linhas, caminho_saida):
    linhas_com_problemas = []

    for i, linha in enumerate(linhas, start=1):
        especiais = encontrar_caracteres_especiais_com_pos(linha)
        if especiais:
            linhas_com_problemas.append((i, especiais, linha.strip()))

    if not linhas_com_problemas:
        return

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("⚠️ Caracteres especiais encontrados nas seguintes linhas:\n\n")
        f.write(f"{'Linha':<8} {'Caracteres encontrados':<45} {'Conteúdo da linha'}\n")
        f.write("-" * 100 + "\n")

        for num_linha, chars_pos, conteudo in linhas_com_problemas:
            chars_descritos = ", ".join(f"{repr(c)}(pos {pos})" for pos, c in chars_pos)
            f.write(f"{str(num_linha):<8} {chars_descritos:<45} {conteudo}\n")


def verificar_dados_bancarios_vazios(banco, agencia, conta):
    problemas = []
    if not banco:
        problemas.append("Banco vazio")
    if not agencia:
        problemas.append("Agência vazia")
    if not conta:
        problemas.append("Conta vazia")
    return problemas


def processar_cnab240(linhas):
    registros = []
    registro_atual = None

    contagem_contas = defaultdict(int)
    mapa_cpfs = defaultdict(set)
    duplicados = []

    for num, linha in enumerate(linhas, start=1):

        if len(linha) < 140:
            continue

        tipo = linha[13]

        # ================= REGISTRO A =================
        if tipo == "A":
            banco = linha[0:3].strip()
            agencia = linha[23:28].strip()
            conta = linha[29:41].strip()

            problemas = verificar_dados_bancarios_vazios(banco, agencia, conta)

            chave = (banco, agencia, conta)
            contagem_contas[chave] += 1

            if contagem_contas[chave] > 1:
                duplicados.append((num, banco, agencia, conta))

            nome = linha[43:73].strip()
            codom = linha[78:84].strip()
            prec_cp = linha[84:93].strip()
            data_pag = linha[93:101].strip()
            valor = linha[126:134].strip()

            texto = (
                f"Banco: {banco} | Agência: {agencia} | Conta: {conta} | Nome: {nome} | "
                f"CODOM: {codom} | PREC/CP: {prec_cp} | Data Pagamento: {data_pag} | Valor: {valor}"
            )

            registro_atual = {
                "1A": texto,
                "2B": None,
                "problemas": problemas,
                "banco": banco,
                "agencia": agencia,
                "conta": conta
            }

        # ================= REGISTRO B =================
        elif tipo == "B" and registro_atual:
            cpf = linha[21:33].strip()
            registro_atual["2B"] = f"CPF: {cpf}"

            chave = (
                registro_atual.get("banco"),
                registro_atual.get("agencia"),
                registro_atual.get("conta")
            )

            mapa_cpfs[chave].add(cpf)

            registros.append(registro_atual)
            registro_atual = None

    return registros, duplicados, contagem_contas, mapa_cpfs


def gerar_relatorio(registros, caminho_saida):
    if not registros:
        return 0.0

    cabecalhos = ["Nº", "Banco", "Agência", "Conta", "Nome", "CODOM", "PREC/CP", "Data Pgto", "Valor (R$)", "CPF"]
    larguras = [5, 8, 10, 15, 30, 10, 12, 12, 15, 15]

    total_valores = 0.0

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write(" | ".join(h.ljust(w) for h, w in zip(cabecalhos, larguras)) + "\n")
        f.write("-" * (sum(larguras) + 3 * (len(cabecalhos) - 1)) + "\n")

        for i, reg in enumerate(registros, start=1):

            partes = reg["1A"].split("|")

            dados = {}
            for p in partes:
                if ":" in p:
                    chave, valor = p.split(":", 1)
                    dados[chave.strip()] = valor.strip()

            cpf = reg["2B"].replace("CPF:", "").strip() if reg["2B"] else ""

            valor_str = dados.get("Valor", "").replace(",", "").replace(".", "").strip()

            try:
                valor_float = float(valor_str) / 100
                total_valores += valor_float
            except:
                valor_float = 0.0

            valor_fmt = f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            linha_dados = [
                str(i),
                dados.get("Banco", ""),
                reg.get("agencia", ""),
                reg.get("conta", ""),
                dados.get("Nome", ""),
                dados.get("CODOM", ""),
                dados.get("PREC/CP", ""),
                dados.get("Data Pagamento", ""),
                valor_fmt,
                cpf,
            ]

            f.write(" | ".join(d.ljust(w) for d, w in zip(linha_dados, larguras)) + "\n")

        f.write("-" * (sum(larguras) + 3 * (len(cabecalhos) - 1)) + "\n")

        total_fmt = f"{total_valores:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        f.write(f"{'TOTAL GERAL:'.ljust(sum(larguras) - 20)} {total_fmt.rjust(20)}\n")

    return total_valores

# ============================================================
#NOVA FUNÇÃO DO RELATÓRIO DE VALORES > 260.000,00
# ============================================================

def gerar_relatorio_valores_altos(linhas, caminho_saida):
    registros_altos = []

    for linha in linhas:

        if len(linha) < 140:
            continue

        if linha[13] != "A":
            continue

        valor_str = linha[126:134].strip()

        if not valor_str.isdigit():
            continue

        valor_num = int(valor_str)

        if valor_num > 26000000:  # 260.000,00

            nome = linha[43:73].strip()
            codom = linha[78:84].strip()
            prec_cp = linha[84:93].strip()

            valor_fmt = f"{valor_num/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            registros_altos.append((nome, codom, prec_cp, valor_fmt))

    # 👉 só gera se tiver dados
    if not registros_altos:
        return

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DE VALORES ACIMA DE R$ 260.000,00\n")
        f.write("-" * 80 + "\n")
        f.write(f"{'Nome':<35} {'CODOM':<10} {'PREC/CP':<12} {'Valor':<12}\n")
        f.write("-" * 80 + "\n")

        for nome, codom, prec_cp, valor_fmt in registros_altos:
            f.write(f"{nome:<35} {codom:<10} {prec_cp:<12} {valor_fmt:<12}\n")

        
def gerar_relatorio_inconsistencias(pasta, nome_base, duplicados, registros, contagem_contas, mapa_cpfs):

    tem_duplicado = any(qtd > 1 for qtd in contagem_contas.values())
    tem_vazio = any(reg.get("problemas") for reg in registros)

    if not tem_duplicado and not tem_vazio:
        return

    caminho = os.path.join(pasta, f"{nome_base}_inconsistencias.txt")

    with open(caminho, "w", encoding="utf-8") as f:
        f.write("RELATÓRIO DE INCONSISTÊNCIAS BANCÁRIAS\n")
        f.write("-" * 80 + "\n\n")

        # DUPLICADOS COM CPF
        if tem_duplicado:
            f.write("DADOS BANCÁRIOS DUPLICADOS:\n")

            for (banco, agencia, conta), qtd in contagem_contas.items():
                if qtd > 1:
                    f.write(f"{banco} / {agencia} / {conta} -> {qtd} ocorrências\n")

                    cpfs = mapa_cpfs.get((banco, agencia, conta), set())
                    if cpfs:
                        f.write("CPFs envolvidos: " + ", ".join(sorted(cpfs)) + "\n")

                    f.write("\n")

        # CAMPOS VAZIOS
        if tem_vazio:
            f.write("CAMPOS VAZIOS:\n")
            for i, reg in enumerate(registros, start=1):
                if reg.get("problemas"):
                    f.write(f"Registro {i}: {', '.join(reg['problemas'])}\n")


def registrar_resumo(caminho_resumo, nome_relatorio, total):
    with open(caminho_resumo, "a", encoding="utf-8") as f:
        total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        f.write(f"{nome_relatorio:<50} TOTAL: {total_fmt}\n")


# ================= PROGRAMA PRINCIPAL =================

pasta = r"C:\Python\Programas funcionando\Arquivos de bancos"

if not os.path.exists(pasta):
    sys.exit()

arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(".txt")]

if not arquivos:
    sys.exit()

caminho_resumo = os.path.join(pasta, "Resumo_dos_relatorios.txt")

open(caminho_resumo, "w", encoding="utf-8").write(
    "RELATÓRIO RESUMO DOS TOTAIS\n----------------------------------------------\n"
)

for arquivo in arquivos:

    caminho_arquivo = os.path.join(pasta, arquivo)
    linhas = carregar_arquivo(caminho_arquivo)

    if not linhas:
        continue

    nome_base = os.path.splitext(arquivo)[0]

    relatorio_caracteres = os.path.join(pasta, f"{nome_base}_caracteres_especiais.txt")
    verificar_caracteres_especiais_em_todas_linhas(linhas, relatorio_caracteres)

    registros, duplicados, contagem_contas, mapa_cpfs = processar_cnab240(linhas)

    gerar_relatorio_inconsistencias(
        pasta, nome_base, duplicados, registros, contagem_contas, mapa_cpfs
    )

    relatorio_cnab = os.path.join(pasta, f"{nome_base}_relatorio.txt")
    total_relatorio = gerar_relatorio(registros, relatorio_cnab)

    registrar_resumo(caminho_resumo, f"{nome_base}_relatorio.txt", total_relatorio)
    
    # NOVO RELATÓRIO DE VALORES ALTOS
    relatorio_altos = os.path.join(pasta, f"{nome_base}_valores_acima_de_260000.txt") 
    
    gerar_relatorio_valores_altos(linhas, relatorio_altos)