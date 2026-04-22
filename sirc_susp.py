import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import re


def executar_programa(file_path, pasta_saida, mes_referencia, ano_4):

    ano_2 = ano_4[-2:]
    total_registros = 0
    total_arquivos = 0

    if not file_path.lower().endswith(".xlsx"):
        raise ValueError("Somente arquivos .xlsx são permitidos.")

    df = pd.read_excel(file_path, engine="openpyxl", dtype={"DT_OBITO_SIRC2": str})

    df.columns = df.columns.str.strip()
    df.rename(columns={"PREC_CP": "PREC/CP"}, inplace=True)

    if "PREC/CP" not in df.columns:
        raise KeyError("A coluna 'PREC/CP' não foi encontrada no arquivo Excel.")

    # LIMPEZA DO PREC/CP
    df["PREC/CP"] = (
        df["PREC/CP"]
        .astype(str)
        .str.replace(".0", "", regex=False)
        .str.replace(r"\D", "", regex=True)
        .str.strip()
    )

    df = df[df["PREC/CP"].str.len() > 0]
    df["PREC/CP"] = df["PREC/CP"].str.lstrip("0")

    # CLASSIFICAÇÃO
    df["TIPO"] = None
    df.loc[df["PREC/CP"].str.contains(r"^0*96"), "TIPO"] = "MILITAR VETERANO"
    df.loc[df["PREC/CP"].str.contains(r"^0*98"), "TIPO"] = "PENSIONISTA"
    df = df[df["TIPO"].notna()].copy()

    print("\nAMOSTRA PREC/CP LIMPO:")
    print(df["PREC/CP"].head(10))

    if df.empty:
        raise ValueError(
            "Nenhum registro iniciado com 96 ou 98 foi encontrado.\n"
            "Verifique se a coluna PREC/CP está correta no Excel."
        )

    # DATA
    df["DT_OBITO_SIRC2"] = pd.to_datetime(df["DT_OBITO_SIRC2"], errors="coerce")

    if df["DT_OBITO_SIRC2"].isna().any():
        raise ValueError("Existem datas inválidas na coluna DT_OBITO_SIRC2.")

    df["MES"] = df["DT_OBITO_SIRC2"].dt.month.astype(int)
    df["ANO"] = df["DT_OBITO_SIRC2"].dt.year.astype(int)
    df["DIA"] = df["DT_OBITO_SIRC2"].dt.day.astype(int)

    df["DT_OBITO_FORMATADA"] = df["DT_OBITO_SIRC2"].dt.strftime("%d%m%Y")

    tipos = df["TIPO"].unique()

    # PROCESSAMENTO
    for tipo in tipos:

        df_situacao = df[df["TIPO"] == tipo].copy()
        linhas = []

        for _, row in df_situacao.iterrows():

            prec_cp = row["PREC/CP"]
            data_obito_dt = row["DT_OBITO_SIRC2"]
            data_obito = row["DT_OBITO_FORMATADA"]

            if data_obito_dt.year == int(ano_4) and data_obito_dt.month == int(mes_referencia):

                if tipo == "MILITAR VETERANO":
                    data_formatada = data_obito
                elif tipo == "PENSIONISTA":
                    data_formatada = data_obito[:4] + data_obito[6:8]
                else:
                    data_formatada = data_obito[:4] + data_obito[4:8]

                data_formatada_alinhada = data_formatada.ljust(10)

                if tipo == "MILITAR VETERANO":
                    linha_data_limite = (
                        f"2{prec_cp}40  {data_formatada_alinhada}                                      "
                        "017178999999119999 Alteração de Data Limite por ter constado no Relatório "
                        "de cruzamentos de dados entre Base SIAPPES e SIRC"
                    )
                else:
                    linha_data_limite = (
                        f"2{prec_cp}21  {data_formatada_alinhada}                                      "
                        "017178999999119999 Alteração de Data Limite por ter constado no Relatório "
                        "de cruzamentos de dados entre Base SIAPPES e SIRC"
                    )

                linhas.append(linha_data_limite)

                mes_int = int(mes_referencia)

                if row["DIA"] >= 15:
                    adicional = mes_int
                else:
                    adicional = 12 if mes_int == 1 else mes_int - 1

                adicional_meses = f"{adicional:02d}"

                prefixo_rubrica = "B" if tipo == "MILITAR VETERANO" else "C"

                if tipo == "MILITAR VETERANO":
                    linha_c86m = (
                        f"1{prec_cp}35  {prefixo_rubrica}86M{adicional_meses}     {mes_referencia}{ano_2}                                 "
                        "017178999999119999 Saque do Adic Natal proporcional por ter constado no Relatório "
                        "de cruzamentos de dados entre Base SIAPPES e SIRC"
                    )
                else:
                    linha_c86m = (
                        f"1{prec_cp}40  {prefixo_rubrica}86M{adicional_meses}     {mes_referencia}{ano_2}                                 "
                        "017178999999119999 Saque do Adic Natal proporcional por ter constado no Relatório "
                        "de cruzamentos de dados entre Base SIAPPES e SIRC"
                    )

                linhas.append(linha_c86m)

            else:
                linha_calculo_3 = (
                    f"2{prec_cp}07  3          {mes_referencia}{ano_4}  000000                       "
                    "017178999999119999 Alteração de Cálculo por ter constado no Relatório "
                    "de cruzamentos de dados entre Base SIAPPES e SIRC"
                )
                linhas.append(linha_calculo_3)

        if linhas:

            total_registros += len(linhas)

            output_file = os.path.join(
                pasta_saida,
                f"arquivo_para_importacao_{tipo.lower().replace(' ', '_')}.txt"
            )

            with open(output_file, "w", encoding="utf-8", newline="") as f:
                for linha in linhas:
                    f.write(linha + "\r\n")

            total_arquivos += 1

    return total_registros, total_arquivos


# ================= FILTRO SUSPENSÃO =================

def aplicar_filtro_suspensao(pasta_saida, arquivo_suspensao):

    with open(arquivo_suspensao, "r", encoding="latin-1", errors="ignore") as f:
        conteudo = f.read()

    precs = set(re.findall(r'PREC.*?(\d{9,11})', conteudo, re.IGNORECASE))
    precs = {p.zfill(11) for p in precs}

    print("\nPREC carregados da suspensão:", precs)

    total_removidos = 0

    arquivos = [
        f for f in os.listdir(pasta_saida)
        if f.startswith("arquivo_para_importacao_")
    ]

    for nome_arquivo in arquivos:
        caminho = os.path.join(pasta_saida, nome_arquivo)

        with open(caminho, "r", encoding="utf-8") as f:
            linhas = f.readlines()

        novas_linhas = []

        for linha in linhas:

            match = re.match(r'[12](\d{9})', linha)

            if not match:
                novas_linhas.append(linha)
                continue

            prec = match.group(1).zfill(11)

            if prec in precs:
                total_removidos += 1
                continue

            novas_linhas.append(linha)

        # ✔️ grava arquivo correto
        with open(caminho, "w", encoding="utf-8") as f:
            f.writelines(novas_linhas)

    return total_removidos


# ================= INTERFACE =================

def selecionar_arquivo(entry):
    caminho = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, caminho)


def selecionar_excel():
    selecionar_arquivo(entry_excel)


def selecionar_pasta():
    caminho = filedialog.askdirectory()
    entry_pasta.delete(0, tk.END)
    entry_pasta.insert(0, caminho)


def executar():
    file_path = entry_excel.get()
    pasta_saida = entry_pasta.get()
    arquivo_suspensao = entry_suspensao.get()
    mes_referencia = entry_mes.get().zfill(2)
    ano_referencia = entry_ano.get()

    if not file_path or not pasta_saida or not mes_referencia or not ano_referencia:
        messagebox.showwarning("Atenção", "Preencha todos os campos.")
        return

    try:
        total_registros, total_arquivos = executar_programa(
            file_path, pasta_saida, mes_referencia, ano_referencia
        )

        total_removidos = 0

        if arquivo_suspensao:
            total_removidos = aplicar_filtro_suspensao(
                pasta_saida, arquivo_suspensao
            )

        messagebox.showinfo(
            "Sucesso",
            f"Arquivos gerados: {total_arquivos}\n"
            f"Registros gerados: {total_registros}\n"
            f"Removidos por suspensão: {total_removidos}"
        )

    except Exception as e:
        messagebox.showerror("Erro", str(e))


janela = tk.Tk()
janela.title("Gerador SIRC")
janela.geometry("650x400")

tk.Label(janela, text="Arquivo Excel (.xlsx):").pack()
entry_excel = tk.Entry(janela, width=90)
entry_excel.pack()
tk.Button(janela, text="Selecionar Excel", command=selecionar_excel).pack(pady=5)

tk.Label(janela, text="Arquivo de Suspensão (TXT):").pack()
entry_suspensao = tk.Entry(janela, width=90)
entry_suspensao.pack()
tk.Button(janela, text="Selecionar TXT", command=lambda: selecionar_arquivo(entry_suspensao)).pack(pady=5)

tk.Label(janela, text="Pasta de saída:").pack()
entry_pasta = tk.Entry(janela, width=90)
entry_pasta.pack()
tk.Button(janela, text="Selecionar Pasta", command=selecionar_pasta).pack(pady=5)

tk.Label(janela, text="Mês de referência (MM):").pack()
entry_mes = tk.Entry(janela, width=10)
entry_mes.pack()

tk.Label(janela, text="Ano (AAAA):").pack()
entry_ano = tk.Entry(janela, width=10)
entry_ano.pack()

tk.Button(
    janela,
    text="EXECUTAR",
    bg="green",
    fg="white",
    width=25,
    height=2,
    command=executar
).pack(pady=20)

janela.mainloop()