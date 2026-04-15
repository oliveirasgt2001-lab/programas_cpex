import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime


def executar_programa(file_path, pasta_saida, mes_referencia, ano_4):

    ano_2 = ano_4[-2:]
    total_registros = 0
    total_arquivos = 0

    data_referencia = datetime(int(ano_4), int(mes_referencia), 1)

    if not file_path.lower().endswith(".xlsx"):
        raise ValueError("Somente arquivos .xlsx são permitidos.")

    df = pd.read_excel(file_path, engine="openpyxl", dtype={"DT_OBITO_SIRC2": str})

    df.columns = df.columns.str.strip()
    df.rename(columns={"PREC_CP": "PREC/CP"}, inplace=True)

    if "PREC/CP" not in df.columns:
        raise KeyError("A coluna 'PREC/CP' não foi encontrada no arquivo Excel.")

    # ==============================
    # CLASSIFICAÇÃO PELO PREC/CP
    # ==============================

    df["PREC/CP"] = df["PREC/CP"].astype(str).str.strip()

    df["TIPO"] = None
    df.loc[df["PREC/CP"].str.startswith("96"), "TIPO"] = "MILITAR VETERANO"
    df.loc[df["PREC/CP"].str.startswith("98"), "TIPO"] = "PENSIONISTA"

    # Mantém apenas 96 e 98
    df = df[df["TIPO"].notna()].copy()

    if df.empty:
        raise ValueError("Nenhum registro iniciado com 96 ou 98 foi encontrado.")

    # ==============================
    # TRATAMENTO DE DATA
    # ==============================

    df["DT_OBITO_SIRC2"] = pd.to_datetime(df["DT_OBITO_SIRC2"], errors="coerce")

    if df["DT_OBITO_SIRC2"].isna().any():
        raise ValueError("Existem datas inválidas na coluna DT_OBITO_SIRC2.")

    df["MES"] = df["DT_OBITO_SIRC2"].dt.month.astype(int)
    df["ANO"] = df["DT_OBITO_SIRC2"].dt.year.astype(int)
    df["DIA"] = df["DT_OBITO_SIRC2"].dt.day.astype(int)

    df["DT_OBITO_FORMATADA"] = df["DT_OBITO_SIRC2"].dt.strftime("%d%m%Y")

    tipos = df["TIPO"].unique()

    for tipo in tipos:

        df_situacao = df[df["TIPO"] == tipo].copy()
        linhas = []

        for _, row in df_situacao.iterrows():

            prec_cp = str(row["PREC/CP"])
            data_obito_dt = row["DT_OBITO_SIRC2"]
            data_obito = row["DT_OBITO_FORMATADA"]

            # ==============================
            # REGRA PRINCIPAL
            # ==============================

            if data_obito_dt.year == int(ano_4) and data_obito_dt.month == int(mes_referencia):

                # ---------- DATA FORMATADA ----------

                if tipo == "MILITAR VETERANO":
                    data_formatada = data_obito
                elif tipo == "PENSIONISTA":
                    data_formatada = data_obito[:4] + data_obito[6:8]
                else:
                    data_formatada = data_obito[:4] + data_obito[4:8]

                data_formatada_alinhada = data_formatada.ljust(10)

                # ---------- DATA LIMITE ----------

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

                # ---------- CÁLCULO ADICIONAL ----------

                adicional_meses = "{:02d}".format(
                    int(mes_referencia) if row["DIA"] >= 15 else int(mes_referencia) - 1
                )

                if tipo == "MILITAR VETERANO":
                    prefixo_rubrica = "B"
                elif tipo == "PENSIONISTA":
                    prefixo_rubrica = "C"
                else:
                    prefixo_rubrica = "X"

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
                # ---------- CÁLCULO 3 ----------
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
                    f.write(linha + "\n")

            total_arquivos += 1

    return total_registros, total_arquivos


# ================= INTERFACE =================

def selecionar_excel():
    caminho = filedialog.askopenfilename(
        filetypes=[("Arquivos Excel", "*.xlsx")]
    )
    entry_excel.delete(0, tk.END)
    entry_excel.insert(0, caminho)


def selecionar_pasta():
    caminho = filedialog.askdirectory()
    entry_pasta.delete(0, tk.END)
    entry_pasta.insert(0, caminho)


def executar():
    file_path = entry_excel.get()
    pasta_saida = entry_pasta.get()
    mes_referencia = entry_mes.get().zfill(2)
    ano_referencia = entry_ano.get()

    if not file_path or not pasta_saida or not mes_referencia or not ano_referencia:
        messagebox.showwarning("Atenção", "Preencha todos os campos.")
        return

    if not mes_referencia.isdigit() or not (1 <= int(mes_referencia) <= 12):
        messagebox.showerror("Erro", "O mês deve estar entre 01 e 12.")
        return

    try:
        total_registros, total_arquivos = executar_programa(
            file_path, pasta_saida, mes_referencia, ano_referencia
        )

        messagebox.showinfo(
            "Sucesso",
            f"Processamento concluído com sucesso!\n\n"
            f"Arquivos gerados: {total_arquivos}\n"
            f"Total de registros gerados: {total_registros}"
        )

    except Exception as e:
        messagebox.showerror("Erro", str(e))


janela = tk.Tk()
janela.title("Gerador SIRC")
janela.geometry("650x350")

tk.Label(janela, text="Arquivo Excel (.xlsx):").pack()
entry_excel = tk.Entry(janela, width=90)
entry_excel.pack()
tk.Button(janela, text="Selecionar Excel", command=selecionar_excel).pack(pady=5)

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