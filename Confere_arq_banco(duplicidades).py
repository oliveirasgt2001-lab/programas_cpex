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
        return False  # 🔥 retorno novo

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("⚠️ Caracteres especiais encontrados nas seguintes linhas:\n\n")
        f.write(f"{'Linha':<8} {'Caracteres encontrados':<45} {'Conteúdo da linha'}\n")
        f.write("-" * 100 + "\n")

        for num_linha, chars_pos, conteudo in linhas_com_problemas:
            chars_descritos = ", ".join(f"{repr(c)}(pos {pos})" for pos, c in chars_pos)
            f.write(f"{str(num_linha):<8} {chars_descritos:<45} {conteudo}\n")

    return True  # 🔥 retorno novo


def verificar_dados_bancarios_vazios(banco, agencia, conta):
    problemas = []
    if not banco:
        problemas.append("Banco vazio")
    if not agencia:
        problemas.append("Agência vazia")
    if not conta:
        problemas.append("Conta vazia")
    return problemas


def processar_cnab240(linhas, nome_arquivo):

    registros = []
    registro_atual = None

    contagem_contas = defaultdict(int)

    mapa_detalhado = defaultdict(lambda: {
        "cpfs": set(),
        "arquivos": set(),
        "precs": set()
    })

    for num, linha in enumerate(linhas, start=1):

        if len(linha) < 140:
            continue

        tipo = linha[13]

        if tipo == "A":
            banco = linha[0:3].strip()
            agencia = linha[23:28].strip()
            conta = linha[29:41].strip()

            problemas = verificar_dados_bancarios_vazios(banco, agencia, conta)

            chave = (banco, agencia, conta)
            contagem_contas[chave] += 1

            nome = linha[43:73].strip()
            codom = linha[78:84].strip()
            prec_cp = linha[84:93].strip()
            data_pag = linha[93:101].strip()
            valor = linha[126:134].strip()

            registro_atual = {
                "banco": banco,
                "agencia": agencia,
                "conta": conta,
                "prec_cp": prec_cp,
                "nome": nome,
                "valor_bruto": valor
            }

        elif tipo == "B" and registro_atual:
            cpf = linha[21:33].strip()

            chave = (
                registro_atual["banco"],
                registro_atual["agencia"],
                registro_atual["conta"]
            )

            mapa_detalhado[chave]["cpfs"].add(cpf)
            mapa_detalhado[chave]["arquivos"].add(nome_arquivo)
            mapa_detalhado[chave]["precs"].add(registro_atual["prec_cp"])

            valor_str = registro_atual["valor_bruto"].replace(",", "").replace(".", "").strip()

            try:
                valor_float = float(valor_str) / 100
                valor_fmt = f"{valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except:
                valor_fmt = "0,00"

            registro_atual["cpf"] = cpf
            registro_atual["valor"] = valor_fmt

            registros.append(registro_atual)
            registro_atual = None

    return registros, contagem_contas, mapa_detalhado


def gerar_relatorio(registros, caminho_saida):
    if not registros:
        return 0.0

    total_valores = 0.0

    with open(caminho_saida, "w", encoding="utf-8") as f:
        for reg in registros:
            valor_str = reg.get("valor_bruto", "").replace(",", "").replace(".", "").strip()
            try:
                total_valores += float(valor_str) / 100
            except:
                pass

    return total_valores


# ================= RESUMO MELHORADO =================
def registrar_resumo_completo(caminho, nome_arquivo, total, registros, linhas, teve_caractere):

    with open(caminho, "a", encoding="utf-8") as f:

        total_fmt = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        f.write("=" * 80 + "\n")
        f.write(f"ARQUIVO: {nome_arquivo}\n")
        f.write("=" * 80 + "\n")

        # 🔹 Total financeiro
        f.write(f"TOTAL (R$): {total_fmt}\n")

        # 🔹 Total beneficiários
        total_benef = len(registros)
        f.write(f"TOTAL DE BENEFICIÁRIOS: {total_benef}\n\n")

        # 🔹 Valores acima de 260 mil
        f.write("BENEFICIÁRIOS COM VALORES ACIMA DE 260.000:\n")
        encontrou_altos = False

        for linha in linhas:
            if len(linha) < 140:
                continue

            if linha[13] != "A":
                continue

            valor_str = linha[126:134].strip()

            if valor_str.isdigit() and int(valor_str) > 26000000:
                nome = linha[43:73].strip()
                codom = linha[78:84].strip()
                valor_fmt = f"{int(valor_str)/100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                f.write(f"- {nome} | CODOM: {codom} | Valor: {valor_fmt}\n")
                encontrou_altos = True

        if not encontrou_altos:
            f.write("Nenhum encontrado.\n")

        f.write("\n")

        # 🔹 Caracteres especiais
        f.write("CARACTERES ESPECIAIS:\n")
        if teve_caractere:
            f.write("Há registros com caracteres especiais. Ver relatório específico.\n")
        else:
            f.write("Nenhum caractere especial encontrado.\n")

        f.write("\n\n")


# ================= PROGRAMA PRINCIPAL =================

pasta = r"E:\Python\Arquivos de bancos"

if not os.path.exists(pasta):
    sys.exit()

arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(".txt")]

if not arquivos:
    sys.exit()

caminho_resumo = os.path.join(pasta, "Resumo_dos_relatorios.txt")

open(caminho_resumo, "w", encoding="utf-8").write(
    "RELATÓRIO RESUMO CONSOLIDADO\n\n"
)

for arquivo in arquivos:

    caminho_arquivo = os.path.join(pasta, arquivo)
    linhas = carregar_arquivo(caminho_arquivo)

    if not linhas:
        continue

    nome_base = os.path.splitext(arquivo)[0]

    relatorio_caracteres = os.path.join(pasta, f"{nome_base}_caracteres_especiais.txt")
    teve_caractere = verificar_caracteres_especiais_em_todas_linhas(linhas, relatorio_caracteres)

    registros, _, _ = processar_cnab240(linhas, arquivo)

    total = gerar_relatorio(registros, os.path.join(pasta, f"{nome_base}_relatorio.txt"))

    registrar_resumo_completo(
        caminho_resumo,
        arquivo,
        total,
        registros,
        linhas,
        teve_caractere
    )