import os
import sys
import re
from collections import defaultdict


# ================= FUNÇÕES AUXILIARES =================

def formatar_valor(valor_str):
    try:
        valor = float(valor_str.replace(",", "").replace(".", "")) / 100
        return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "0,00"


def linha_separadora(larguras):
    return "-" * (sum(larguras) + 3 * (len(larguras) - 1))

def formatar_data(data_str):
        if len(data_str) == 8 and data_str.isdigit():
            return f"{data_str[0:2]}/{data_str[2:4]}/{data_str[4:8]}"
        return data_str


# ================= FUNÇÕES =================

def carregar_arquivo(caminho):
    if not os.path.exists(caminho):
        return []
    try:
        with open(caminho, "r", encoding="utf-8") as arq:
            return arq.readlines()
    except:
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

    # 🔴 NÃO GERA ARQUIVO
    if not linhas_com_problemas:
        return

    with open(caminho_saida, "w", encoding="utf-8") as f:

        cab = ["Linha", "Caracteres", "Conteúdo"]
        larg = [8, 50, 80]

        f.write(" | ".join(h.ljust(w) for h, w in zip(cab, larg)) + "\n")
        f.write(linha_separadora(larg) + "\n")

        for num_linha, chars_pos, conteudo in linhas_com_problemas:
            chars_descritos = ", ".join(f"{c}(p{pos})" for pos, c in chars_pos)

            linha_dados = [
                str(num_linha),
                chars_descritos,
                conteudo[:80]
            ]

            f.write(" | ".join(d.ljust(w) for d, w in zip(linha_dados, larg)) + "\n")


def processar_cnab240(linhas, nome_arquivo):

    registros = []
    registro_atual = None

    contagem_contas = defaultdict(int)

    mapa_detalhado = defaultdict(lambda: {
        "cpfs": set(),
        "arquivos": set(),
        "precs": set()
    })

    for linha in linhas:

        if len(linha) < 140:
            continue

        tipo = linha[13]

        if tipo == "A":
            registro_atual = {
            "banco": linha[0:3].strip(),
            "agencia": linha[23:28].strip(),
            "conta": linha[29:41].strip(),
            "prec_cp": linha[84:93].strip(),
            "data_pagamento": linha[93:101].strip(),
            "nome": linha[43:73].strip(),
            "valor_bruto": linha[126:134].strip()
            }

            def campo_vazio_ou_zerado(valor):
                return not valor or valor.strip("0") == ""

            if (
                campo_vazio_ou_zerado(registro_atual["banco"]) or
                campo_vazio_ou_zerado(registro_atual["agencia"]) or
                campo_vazio_ou_zerado(registro_atual["conta"])
    ):
                registro_atual["dados_bancarios_vazios"] = True
            else:
                registro_atual["dados_bancarios_vazios"] = False

    # 🔴 CONTAGEM SÓ SE NÃO FOR VAZIO
            if not registro_atual["dados_bancarios_vazios"]:
                chave = (registro_atual["banco"], registro_atual["agencia"], registro_atual["conta"])
                contagem_contas[chave] += 1

        elif tipo == "B" and registro_atual is not None:

            cpf = linha[21:33].strip()

            chave = (
                registro_atual["banco"],
                registro_atual["agencia"],
                registro_atual["conta"]
            )

            mapa_detalhado[chave]["cpfs"].add(cpf)
            mapa_detalhado[chave]["arquivos"].add(nome_arquivo)
            mapa_detalhado[chave]["precs"].add(registro_atual["prec_cp"])

            registro_atual["cpf"] = cpf
            registro_atual["valor"] = formatar_valor(registro_atual["valor_bruto"])

            registros.append(registro_atual)
            registro_atual = None

    return registros, contagem_contas, mapa_detalhado


def gerar_relatorio(registros, caminho_saida):

    cab = ["Nº", "Banco", "Agência", "Conta", "Nome", "PREC/CP", "Data", "Valor (R$)", "CPF", "Dados Vazios"]
    larg = [4, 6, 8, 14, 30, 10, 12, 14, 14, 14]

    total = 0.0

    with open(caminho_saida, "w", encoding="utf-8") as f:

        f.write(" | ".join(h.ljust(w) for h, w in zip(cab, larg)) + "\n")
        f.write(linha_separadora(larg) + "\n")

        if not registros:
            f.write("Nenhum registro encontrado.\n")
            f.write(linha_separadora(larg) + "\n")
            f.write(f"{'TOTAL GERAL:'.ljust(sum(larg)-20)} {'0,00'.rjust(20)}\n")
            return 0.0

        for i, r in enumerate(registros, 1):

            valor = formatar_valor(r["valor_bruto"])
            data_fmt = formatar_data(r["data_pagamento"])
            flag_vazio = "⚠️ SIM" if r.get("dados_bancarios_vazios") else "OK"
            

            try:
                total += float(r["valor_bruto"]) / 100
            except:
                pass

            linha_dados = [
                str(i),
                r["banco"],
                r["agencia"],
                r["conta"],
                r["nome"][:30],
                r["prec_cp"],
                data_fmt,
                valor,
                r["cpf"],
                flag_vazio
            ]

            f.write(" | ".join(d.ljust(w) for d, w in zip(linha_dados, larg)) + "\n")

        f.write(linha_separadora(larg) + "\n")

        total_fmt = formatar_valor(str(int(total * 100)))
        f.write(f"{'TOTAL GERAL:'.ljust(sum(larg)-20)} {total_fmt.rjust(20)}\n")

    return total


def gerar_relatorio_valores_altos(linhas, caminho_saida):

    registros = []

    for linha in linhas:

        if len(linha) < 140:
            continue

        if linha[13] != "A":
            continue

        valor = linha[126:134].strip()

        if valor.isdigit() and int(valor) > 26000000:

            nome = linha[43:73].strip()
            codom = linha[78:84].strip()
            prec = linha[84:93].strip()

            valor_fmt = formatar_valor(valor)

            registros.append((nome, codom, prec, valor_fmt))
    
    # 🔴 SÓ GERA SE TIVER DADO
    if not registros:
        return

    cab = ["Nome", "CODOM", "PREC/CP", "Valor"]
    larg = [35, 10, 12, 15]

    with open(caminho_saida, "w", encoding="utf-8") as f:

        f.write("VALORES ACIMA DE 260.000\n")
        f.write(linha_separadora(larg) + "\n")

        f.write(" | ".join(h.ljust(w) for h, w in zip(cab, larg)) + "\n")
        f.write(linha_separadora(larg) + "\n")

        for nome, codom, prec, valor_fmt in registros:
            f.write(f"{nome:<35} | {codom:<10} | {prec:<12} | {valor_fmt:>15}\n")


def gerar_relatorio_inconsistencias(pasta, nome_base, registros, contagem_contas, mapa_detalhado):

    linhas_saida = []

    for (b, a, c), qtd in contagem_contas.items():
        if qtd > 1:
            info = mapa_detalhado[(b, a, c)]

            if len(info["cpfs"]) <= 1:
                continue

            linhas_saida.append(
                (b, a, c, qtd, info["cpfs"], info["arquivos"], info["precs"])
            )

    # 🔴 SÓ GERA SE TIVER DADO
    if not linhas_saida:
        return

    caminho = os.path.join(pasta, f"{nome_base}_inconsistencias.txt")

    cab = ["Banco", "Agência", "Conta", "Qtde", "CPFs", "Arquivos", "PREC"]
    larg = [6, 8, 15, 5, 25, 20, 10]

    with open(caminho, "w", encoding="utf-8") as f:

        f.write("DADOS BANCÁRIOS DUPLICADOS (CPFs DIFERENTES)\n")
        f.write(linha_separadora(larg) + "\n")

        f.write(" | ".join(h.ljust(w) for h, w in zip(cab, larg)) + "\n")
        f.write(linha_separadora(larg) + "\n")

        for b, a, c, qtd, cpfs, arquivos, precs in linhas_saida:
            f.write(
                f"{b:<6} | {a:<8} | {c:<15} | {qtd:<5} | "
                f"{', '.join(cpfs)[:25]:<25} | "
                f"{', '.join(arquivos)[:20]:<20} | "
                f"{', '.join(precs)[:10]:<10}\n"
            )

def gerar_relatorio_cpfs_repetidos(pasta, cpf_global):

    conteudo = []

    for cpf, ocorrencias in sorted(cpf_global.items()):
        if len(ocorrencias) > 1:
            conteudo.append((cpf, ocorrencias))

    # 🔴 NÃO GERA SE VAZIO
    if not conteudo:
        return

    caminho = os.path.join(pasta, "CPF_repetido_nos_arquivos.txt")

    with open(caminho, "w", encoding="utf-8") as f:

        # topo do relatório
        f.write("="*100 + "\n\n")

        # cabeçalho novo
        cab = ["CPF", "Valor", "Nome", "Arquivo", "PREC"]
        larg = [18, 15, 30, 25, 10]

        f.write(" | ".join(h.center(w) for h, w in zip(cab, larg)) + "\n")
        f.write(linha_separadora(larg) + "\n")

        # dados
        for cpf, ocorrencias in conteudo:
            for (arq, nome, prec, valor, *_ ) in ocorrencias:
                f.write(
                    f"{cpf:<18} | "
                    f"{valor:>15} | "
                    f"{nome[:30]:<30} | "
                    f"{arq[:25]:<25} | "
                    f"{prec:<10}\n"
                )

        # rodapé
        f.write("="*100 + "\n")

                           
def escrever_cpfs_repetidos_no_resumo(caminho_resumo, cpf_global):

    with open(caminho_resumo, "a", encoding="utf-8") as f:

        f.write("\n" + "="*100 + "\n")
        f.write("CPFs REPETIDOS (RESUMO)\n")
        f.write("="*100 + "\n")

        encontrou = False

        for cpf, ocorrencias in sorted(cpf_global.items()):

            if len(ocorrencias) <= 1:
                continue

            encontrou = True

            f.write(f"\nCPF: {cpf}\n")

            for (arq, nome, prec, valor, banco, agencia, conta) in ocorrencias:

                f.write(
                    f"  Arquivo: {arq:<25} | "
                    f"Banco: {banco:<6} | Ag: {agencia:<8} | Conta: {conta:<12} | "
                    f"Valor: {valor:>12} | PREC: {prec:<10} | "
                    f"Nome: {nome[:25]}\n"
                )

        if not encontrou:
            f.write("Nenhum CPF repetido encontrado.\n")            
            
# ================= MAIN =================

pasta = r"C:\Python\Programas funcionando\Arquivos de bancos"

if not os.path.exists(pasta):
    sys.exit()

arquivos = [f for f in os.listdir(pasta) if f.lower().endswith(".txt")]

if not arquivos:
    sys.exit()

caminho_resumo = os.path.join(pasta, "Resumo_dos_relatorios.txt")

open(caminho_resumo, "w", encoding="utf-8").write("RESUMO GERAL\n" + "="*80 + "\n\n")

cpf_global = defaultdict(list)

for arquivo in arquivos:

    caminho_arquivo = os.path.join(pasta, arquivo)
    linhas = carregar_arquivo(caminho_arquivo)

    if not linhas:
        continue

    nome_base = os.path.splitext(arquivo)[0]

    verificar_caracteres_especiais_em_todas_linhas(
        linhas,
        os.path.join(pasta, f"{nome_base}_caracteres.txt")
    )

    registros, contagem_contas, mapa = processar_cnab240(linhas, arquivo)

# 🔴 COLETA DADOS VAZIOS (AQUI É O LUGAR CERTO)

    dados_vazios = [r for r in registros if r.get("dados_bancarios_vazios")]

    gerar_relatorio_inconsistencias(pasta, nome_base, registros, contagem_contas, mapa)

    total = gerar_relatorio(registros, os.path.join(pasta, f"{nome_base}_relatorio.txt"))

    # ================= DADOS PARA RESUMO =================

    total_seguro = total if total is not None else 0.0
    total_beneficiarios = len(registros)

    # 🔴 Valores altos
    valores_altos = []
    for r in registros:
        try:
            if int(r["valor_bruto"]) > 26000000:
                valores_altos.append((r["cpf"], r["valor"], r["prec_cp"]))
        except:
            pass

    # 🔴 Dados bancários duplicados (CPFs diferentes)
    duplicidades = []
    for chave, qtd in contagem_contas.items():
        if qtd > 1:
            info = mapa[chave]
            if len(info["cpfs"]) > 1:
                duplicidades.append((chave, list(info["cpfs"])))

    # 🔴 CPFs repetidos no arquivo
    cpf_local = defaultdict(int)
    for r in registros:
        cpf_local[r["cpf"]] += 1

    cpfs_repetidos = [cpf for cpf, qtd in cpf_local.items() if qtd > 1]

    # ================= ESCREVE RESUMO =================

    with open(caminho_resumo, "a", encoding="utf-8") as f:

        f.write("="*80 + "\n")
        f.write(f"ARQUIVO: {arquivo}\n")
        f.write("="*80 + "\n")

        f.write(f"TOTAL FINANCEIRO: {formatar_valor(str(int(total_seguro*100)))}\n")
        f.write(f"TOTAL BENEFICIÁRIOS: {total_beneficiarios}\n\n")

        # 🔴 Valores altos
        if valores_altos:
            f.write(">>> PAGAMENTOS ACIMA DE 260 MIL:\n")
            for cpf, valor, prec in valores_altos:
                f.write(f"CPF: {cpf} | VALOR: {valor} | PREC: {prec}\n")
            f.write("\n")

        # 🔴 Duplicidades bancárias
        if duplicidades:
            f.write(">>> DADOS BANCÁRIOS DUPLICADOS (IGUAIS) (CPFs DIFERENTES):\n")
            for (banco, ag, conta), cpfs in duplicidades:
                f.write(f"{banco}-{ag}-{conta} | CPFs: {', '.join(cpfs)}\n")
            f.write("\n")

     
        
        # 🔴 CPFs repetidos (com dados completos)
        if cpfs_repetidos:
            f.write(">>> CPFs REPETIDOS NO ARQUIVO (DETALHADO):\n")
            cab = ["CPF", "Banco", "Agência", "Conta", "Valor", "PREC", "Nome"]
            larg = [14, 6, 8, 14, 12, 10, 25]
            f.write(" | ".join(h.ljust(w) for h, w in zip(cab, larg)) + "\n")
            f.write("-" * (sum(larg) + 3 * (len(larg) - 1)) + "\n")
            for cpf in cpfs_repetidos:
                for r in registros:
                    if r["cpf"] == cpf:
                        
                        f.write(
                        f"{cpf:<14} | "
                        f"{r['banco']:<6} | "
                        f"{r['agencia']:<8} | "
                        f"{r['conta']:<14} | "
                        f"{r['valor']:>12} | "
                        f"{r['prec_cp']:<10} | "
                        f"{r['nome'][:25]:<25}\n"
)

    # mantém relatório separado (igual antes)
    gerar_relatorio_valores_altos(
        linhas,
        os.path.join(pasta, f"{nome_base}_valores_altos.txt")
    )
    # 🔴 RELATÓRIO DE DADOS BANCÁRIOS VAZIOS
    if dados_vazios:
        caminho_vazios = os.path.join(pasta, f"{nome_base}_dados_bancarios_vazios.txt")
        
        with open(caminho_vazios, "w", encoding="utf-8") as f:
            f.write("DADOS BANCÁRIOS VAZIOS\n")
            f.write("="*80 + "\n")

            for r in dados_vazios:
                f.write(
                    f"CPF: {r['cpf']:<14} | "
                    f"Nome: {r['nome'][:30]:<30} | "
                    f"Banco: {r['banco']:<6} | "
                    f"Ag: {r['agencia']:<8} | "
                    f"Conta: {r['conta']:<14} | "
                    f"PREC: {r['prec_cp']}\n"
                )
    
    for r in registros:
            cpf_global[r["cpf"]].append((
                arquivo,
                r["nome"],
                r["prec_cp"],
                r["valor"],
                r["banco"],
                r["agencia"],
                r["conta"]
        ))    
        
escrever_cpfs_repetidos_no_resumo(caminho_resumo, cpf_global)
gerar_relatorio_cpfs_repetidos(pasta, cpf_global)