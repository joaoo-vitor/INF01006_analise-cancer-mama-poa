import asyncio
import os
import re
import ftplib
import tempfile
from pathlib import Path

import pandas as pd
from dbfread import DBF
from pysus.api.extensions import DBC


# =========================================================
# CONFIGURAÇÕES
# =========================================================

FTP_HOST = "ftp.datasus.gov.br"
FTP_DIR = "/dissemin/publicos/SISCAN/SISMAMA/Dados/"


# =========================================================
# CLASSE: PARSER DO .DEF
# =========================================================

class DefParser:

    def __init__(self, def_path):

        self.def_path = def_path

        self.data_pattern = None
        self.data_file_prefix = None

        self.cnv_mappings = {}

        self.dbf_lookups = {}

        self.parse()

    # -----------------------------------------------------

    def parse(self):

        with open(
            self.def_path,
            encoding="latin1"
        ) as f:

            lines = f.readlines()

        # ---------------------------------------------
        # PADRÃO DOS DADOS
        # ---------------------------------------------

        for line in lines:

            match = re.search(
                r"A(.+\.DBC)",
                line,
                re.IGNORECASE
            )

            if match:

                self.data_pattern = (
                    match.group(1).strip().split("\\")[-1]
                )
                self.data_file_prefix = self.data_pattern[:2]

                break

        # ---------------------------------------------
        # MAPEAMENTOS
        # ---------------------------------------------

        for line in lines:

            if "," not in line:
                continue

            parts = [
                p.strip()
                for p in line.split(",")
            ]

            if len(parts) < 4:
                continue

            descricao = parts[0]
            campo = parts[1]
            destino = parts[2]
            arquivo = parts[3]

            # remove L/C/S
            descricao_limpa = re.sub(
                r"^[LCS]",
                "",
                descricao
            )

            # -----------------------------------------
            # CNV
            # -----------------------------------------

            if arquivo.lower().endswith(".cnv"):

                try:
                    coluna = int(destino)
                except:
                    coluna = 1

                if campo not in self.cnv_mappings:

                    self.cnv_mappings[campo] = {

                        "descricao":
                            descricao_limpa,

                        "coluna":
                            coluna,

                        "arquivo":
                            arquivo
                    }

            # -----------------------------------------
            # DBF LOOKUP
            # -----------------------------------------

            elif arquivo.lower().endswith(".dbf"):

                if campo not in self.dbf_lookups:

                    self.dbf_lookups[campo] = {

                        "descricao":
                            descricao_limpa,

                        "campo_destino":
                            destino,

                        "arquivo":
                            arquivo
                    }

    # -----------------------------------------------------

    def show_summary(self):

        print("\n========================")
        print("PADRÃO DOS DADOS")
        print("========================")
        print(self.data_pattern)

        print("\n========================")
        print("CNVs")
        print("========================")

        for campo, info in self.cnv_mappings.items():

            print(
                campo,
                "->",
                info["arquivo"]
            )

        print("\n========================")
        print("LOOKUPS DBF")
        print("========================")

        for campo, info in self.dbf_lookups.items():

            print(
                campo,
                "->",
                info["arquivo"]
            )


# =========================================================
# CLASSE: CONVERSOR DATASUS
# =========================================================

class DatasusConverter:

    def __init__(
        self,
        base_path,
        def_filename,
        filtro_estado="RS"
    ):

        self.base_path = Path(base_path)

        self.def_path = (
            self.base_path / def_filename
        )

        self.filtro_estado = (
            filtro_estado.upper()
        )

        self.parser = DefParser(
            self.def_path
        )

        self.temp_dir = (
            self.base_path / "DADOS"
        )

        self.temp_dir.mkdir(
            exist_ok=True
        )

    # -----------------------------------------------------
    # FTP
    # -----------------------------------------------------

    def connect_ftp(self):

        ftp = ftplib.FTP(FTP_HOST)

        ftp.login()

        ftp.cwd(FTP_DIR)

        return ftp

    # -----------------------------------------------------

    def list_remote_files(self):

        ftp = self.connect_ftp()

        files = ftp.nlst()

        ftp.quit()

        # exemplo:
        # MMRS2401.dbc

        filtered = [

            f for f in files

            if (
                f.upper().endswith(".DBC")
                and f.upper().startswith(self.parser.data_file_prefix)
                and self.filtro_estado
                in f.upper()
            )
        ]

        return filtered

    # -----------------------------------------------------

    def download_files(self):

        ftp = self.connect_ftp()

        remote_files = (
            self.list_remote_files()
        )

        downloaded = []

        print("\n========================")
        print("BAIXANDO ARQUIVOS")
        print("========================")

        for filename in remote_files:

            local_path = (
                self.temp_dir / filename
            )

            if local_path.exists():

                print(
                    f"Já existe: {filename}"
                )

                downloaded.append(
                    local_path
                )

                continue

            print(f"Baixando {filename}")

            with open(local_path, "wb") as f:

                ftp.retrbinary(
                    f"RETR {filename}",
                    f.write
                )

            downloaded.append(local_path)

        ftp.quit()

        return downloaded

    # -----------------------------------------------------
    # LEITURA DOS DBCs
    # -----------------------------------------------------

    def read_dbc_files(self):

        dbc_files = self.download_files()

        dfs = []

        parquet_dir = (
            self.base_path / "parquet"
        )

        parquet_dir.mkdir(
            exist_ok=True
        )

        print("\n========================")
        print("CONVERTENDO DBC -> PARQUET")
        print("========================")

        for dbc_file in dbc_files:

            print(f"\nProcessando {dbc_file.name}")

            try:

                # -----------------------------------------
                # nome parquet
                # -----------------------------------------

                parquet_path = (
                    parquet_dir /
                    f"{dbc_file.stem}.parquet"
                )

                # -----------------------------------------
                # converte dbc -> parquet
                # -----------------------------------------

                if not parquet_path.exists():

                    print(
                        "Convertendo para parquet..."
                    )

                    dbc = DBC(path=str(dbc_file))

                    asyncio.run(
                        dbc.to_parquet(
                            str(parquet_path)
                        )
                    )

                else:

                    print(
                        "Parquet já existe."
                    )

                # -----------------------------------------
                # lê parquet
                # -----------------------------------------

                print("Lendo parquet...")

                df_temp = pd.read_parquet(
                    parquet_path
                )

                df_temp[
                    "ARQUIVO_ORIGEM"
                ] = dbc_file.name

                print(
                    f"{len(df_temp)} registros"
                )

                dfs.append(df_temp)

            except Exception as e:

                print(
                    f"Erro em "
                    f"{dbc_file.name}: {e}"
                )

        if not dfs:

            raise Exception(
                "Nenhum dataframe carregado"
            )

        df = pd.concat(
            dfs,
            ignore_index=True
        )

        return df

    # -----------------------------------------------------
    # CNVs
    # -----------------------------------------------------

    def load_cnv(self, path):

        mapa = {}

        with open(path, encoding="latin1") as f:
            lines = f.readlines()

        # remove cabeçalho
        lines = lines[1:]

        for line in lines:

            line = line.rstrip()

            if not line.strip():
                continue

            parts = re.split(
                r"\s{2,}",
                line.strip()
            )

            if len(parts) < 2:
                continue

            # -----------------------------------------
            # CASO 1
            #
            # 1 Feminino
            # -----------------------------------------

            if len(parts) == 2:

                chave = parts[0].strip()

                descricao = parts[1].strip()

            # -----------------------------------------
            # CASO 2
            #
            # 1 110001 Alta Floresta 110001
            # -----------------------------------------

            else:

                chave = parts[-1].strip()

                descricao = parts[1].strip()

            # remove prefixos numéricos
            descricao = re.sub(
                r"^\d+\s+",
                "",
                descricao
            )

            mapa[chave] = descricao

        return mapa

    # -----------------------------------------------------

    def apply_cnv_mappings(
        self,
        df
    ):

        print("\n========================")
        print("APLICANDO CNVs")
        print("========================")

        for campo, info in (
            self.parser
            .cnv_mappings
            .items()
        ):

            if campo not in df.columns:
                continue

            cnv_path = (
                self.base_path /
                info["arquivo"]
            )

            if not cnv_path.exists():

                print(
                    f"CNV não encontrado: "
                    f"{cnv_path}"
                )

                continue

            print(f"Convertendo {campo}")

            try:

                mapa = self.load_cnv(
                    cnv_path,
                )

                df[campo] = (

                    df[campo]
                    .astype(str)
                    .str.strip()
                    .map(mapa)
                    .fillna(df[campo])

                )

            except Exception as e:

                print(
                    f"Erro em {campo}: {e}"
                )

        return df

    # -----------------------------------------------------
    # DBF LOOKUPS
    # -----------------------------------------------------

    def apply_dbf_lookups(
        self,
        df
    ):

        print("\n========================")
        print("APLICANDO LOOKUPS")
        print("========================")

        for campo, info in (
            self.parser
            .dbf_lookups
            .items()
        ):

            if campo not in df.columns:
                continue

            lookup_path = (
                self.base_path / 
                info["arquivo"]
            )

            if not lookup_path.exists():

                print(
                    f"Lookup não encontrado: "
                    f"{lookup_path}"
                )

                continue

            print(f"Lookup {campo}")

            try:

                lookup_table = DBF(
                    lookup_path,
                    encoding="latin1"
                )

                lookup_df = pd.DataFrame(
                    iter(lookup_table)
                )

                # -----------------------------------------
                # primeira coluna = chave
                # -----------------------------------------

                lookup_key = lookup_df.columns[0]

                # -----------------------------------------
                # coluna destino
                # -----------------------------------------

                lookup_target = (
                    info["campo_destino"]
                )

                # -----------------------------------------
                # caso 1:
                # índice numérico
                # -----------------------------------------

                if str(lookup_target).isdigit():

                    idx = int(lookup_target) - 1

                    if idx >= len(lookup_df.columns):

                        print(
                            f"Índice inválido "
                            f"em {lookup_path}"
                        )

                        continue

                    lookup_value = (
                        lookup_df.columns[idx]
                    )

                # -----------------------------------------
                # caso 2:
                # nome explícito
                # -----------------------------------------

                else:

                    lookup_value = lookup_target

                    if lookup_value not in lookup_df.columns:

                        print(
                            f"{lookup_value} "
                            f"não existe "
                            f"em {lookup_path}"
                        )

                        continue

                # -----------------------------------------
                # reduz tabela
                # -----------------------------------------

                lookup_df = (

                    lookup_df[
                        [
                            lookup_key,
                            lookup_value
                        ]
                    ]

                    .drop_duplicates()

                )

                # -----------------------------------------
                # cria mapa
                # -----------------------------------------

                mapa = dict(

                    zip(
                        lookup_df[lookup_key]
                        .astype(str)
                        .str.strip(),

                        lookup_df[lookup_value]
                    )

                )

                # -----------------------------------------
                # replace da coluna original
                # -----------------------------------------

                df[campo] = (

                    df[campo]
                    .astype(str)
                    .str.strip()
                    .map(mapa)
                    .fillna(df[campo])

                )

            except Exception as e:

                print(
                    f"Erro no lookup "
                    f"{campo}: {e}"
                )

        return df

    # -----------------------------------------------------
    # PIPELINE COMPLETO
    # -----------------------------------------------------

    def process(self):

        self.parser.show_summary()

        # ---------------------------------------------
        # lê dados
        # ---------------------------------------------

        df = self.read_dbc_files()

        print("\n========================")
        print("TOTAL REGISTROS")
        print("========================")

        print(len(df))

        # ---------------------------------------------
        # cnvs
        # ---------------------------------------------

        df = self.apply_cnv_mappings(
            df
        )

        # ---------------------------------------------
        # lookups
        # ---------------------------------------------

        df = self.apply_dbf_lookups(
            df
        )

        return df


# =========================================================
# EXEMPLO DE USO
# =========================================================

if __name__ == "__main__":

    converter = DatasusConverter(

        base_path=r"C:\Users\joaoo\Desktop\TAB_SISMAMA",
        
        def_filename="MMAMA4.def",

        filtro_estado="RS"
    )

    df = converter.process()

    # -----------------------------------------------------
    # EXPORTAÇÃO
    # -----------------------------------------------------

    output_csv = (
        converter.base_path /
        "sismama_rs.csv"
    )

    output_parquet = (
        converter.base_path /
        "sismama_rs.parquet"
    )

    print("\nExportando CSV...")

    df.to_csv(
        output_csv,
        index=False,
        encoding="utf-8-sig"
    )

    print("Exportando Parquet...")

    df.to_parquet(
        output_parquet
    )

    print("\n========================")
    print("FINALIZADO")
    print("========================")

    print(output_csv)
    print(output_parquet)