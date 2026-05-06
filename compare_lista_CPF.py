import os
from collections import defaultdict


def extrair_cpfs_prec(caminho_arquivo):
    dados = defaultdict(set)

    if not os.path.exists(caminho_arquivo):
        print(f"Arquivo não encontrado: {caminho_arquivo}")
        return dados

    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()

            if not linha or "-" not in linha:
                continue

            try:
                partes = linha.split("-")

                if len(partes) < 3:
                    continue

                cpf = partes[1].strip()
                prec = partes[2].strip()

                if cpf:
                    dados[cpf].add(prec)

            except:
                pass

    return dados


def comparar_cpfs(arquivo1, arquivo2, caminho_saida):

    dados_1 = extrair_cpfs_prec(arquivo1)
    dados_2 = extrair_cpfs_prec(arquivo2)

    cpfs_comuns = sorted(set(dados_1.keys()).intersection(dados_2.keys()))

    if not cpfs_comuns:
        print("Nenhum CPF em comum encontrado.")
        return

    with open(caminho_saida, "w", encoding="utf-8") as f:

        f.write("CPFs EM COMUM NOS DOIS ARQUIVOS (COM PREC/CP)\n")
        f.write("="*70 + "\n\n")

        for i, cpf in enumerate(cpfs_comuns, start=1):

            precs_1 = ", ".join(sorted(dados_1[cpf]))
            precs_2 = ", ".join(sorted(dados_2[cpf]))

            f.write(f"{i:06d} - CPF: {cpf}\n")
            f.write(f"        Arquivo 1 PRECs: {precs_1}\n")
            f.write(f"        Arquivo 2 PRECs: {precs_2}\n\n")

    print(f"Relatório gerado em: {caminho_saida}")


# ================= CONFIGURAÇÃO =================

arquivo1 = r"E:\Python\Copia aquivos bancos\Listas_CPF\Lista_Todos_CPFs_1.txt"
arquivo2 = r"E:\Python\Copia aquivos bancos\Listas_CPF\Lista_Todos_CPFs_2.txt"

saida = r"E:\Python\Copia aquivos bancos\Listas_CPF\CPFs_em_comum.txt"

# ================= EXECUÇÃO =================

comparar_cpfs(arquivo1, arquivo2, saida)