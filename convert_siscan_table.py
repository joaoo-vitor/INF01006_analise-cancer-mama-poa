import os
import json
import pandas as pd


def processar_e_traduzir_siscan(caminho_csv, target_key="mamografias", config_file="config.json"):
    """
    Processa um arquivo CSV do SISCAN usando as configurações do config.json.
    - Carrega o CSV.
    - Remove colunas desnecessárias.
    - Traduz valores codificados usando mapeamentos pré-gerados.
    - Renomeia colunas para nomes legíveis.
    """
    
    # 1. Carrega as configurações
    if not os.path.exists(config_file):
        print(f"Erro: Arquivo de configuração '{config_file}' não encontrado.")
        return None

    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    if target_key not in config_data:
        print(f"Erro: Chave '{target_key}' não encontrada no config.json.")
        return None

    config = config_data[target_key]
    mappings = config.get("mappings", {})
    columns_to_drop = config.get("columns_to_drop", [])
    with open(config_file, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    mapa_renomear_colunas = config_data.get("rename", {})

    # 2. Carrega o CSV original
    print(f"Lendo o arquivo CSV: {caminho_csv}...")
    df = pd.read_csv(caminho_csv, sep=";", engine="python")

    # 3. Remove colunas especificadas
    if columns_to_drop:
        cols_to_remove = [c for c in columns_to_drop if c in df.columns]
        if cols_to_remove:
            print(f"Removendo {len(cols_to_remove)} colunas...")
            df.drop(columns=cols_to_remove, inplace=True)

    # 4. Traduz os códigos internos usando os mapeamentos do JSON
    print("Traduzindo os códigos internos...")
    for coluna, dicionario_conversao in mappings.items():
        if coluna in df.columns:
            # Garante que tipos numéricos sejam tratados corretamente se necessário
            if(coluna.startswith("CO")
               or coluna.startswith("NU")
               or coluna.startswith("TP")):
                df[coluna] = df[coluna].astype('Int64')
            
            # Identifica quais chaves são intervalos (ex: "01-10")
            intervalos = {}
            mapeamento_simples = {}
            for k, v in dicionario_conversao.items():
                if "-" in k:
                    try:
                        inicio, fim = map(int, k.split("-"))
                        intervalos[(inicio, fim)] = v
                    except ValueError:
                        mapeamento_simples[k] = v
                else:
                    mapeamento_simples[k] = v

            # Função auxiliar para aplicar a tradução com suporte a intervalos
            def traduzir_valor(val):
                if pd.isna(val):
                    return val
                
                # Tenta mapeamento exato primeiro (convertendo para string)
                s_val = str(val).strip()
                if s_val in mapeamento_simples:
                    return mapeamento_simples[s_val]
                
                # Se não encontrar, tenta os intervalos numéricos
                try:
                    num_val = int(float(s_val))
                    for (inicio, fim), desc in intervalos.items():
                        if inicio <= num_val <= fim:
                            return desc
                except ValueError:
                    pass
                
                return val

            # Aplica a tradução
            df[coluna] = df[coluna].apply(traduzir_valor)
            print(f"  -> Coluna '{coluna}' traduzida com sucesso (considerando intervalos).")
        else:
            # Opcional: Avisar se a coluna do mapeamento não existe no CSV
            pass

    # 5. Renomeia as colunas para formato amigável
    print("Renomeando as colunas para formato amigável...")
    df.rename(columns=mapa_renomear_colunas, inplace=True)

    return df


# --- Exemplo de Uso ---
if __name__ == "__main__":
    import sys

    # Defaults
    caminho_do_seu_csv = r"C:\Users\joaoo\Desktop\SISCAN_MAMOGRAFIA_2024.csv"
    objeto_alvo = "mamografias_atend"

    if len(sys.argv) > 1:
        caminho_do_seu_csv = sys.argv[1]
    if len(sys.argv) > 2:
        objeto_alvo = sys.argv[2]

    if not os.path.exists(caminho_do_seu_csv):
        print(f"Erro: Arquivo CSV '{caminho_do_seu_csv}' não encontrado.")
        sys.exit(1)

    nome_arquivo_base = os.path.splitext(os.path.basename(caminho_do_seu_csv))[0]
    df_final = processar_e_traduzir_siscan(caminho_do_seu_csv, target_key=objeto_alvo)

    if df_final is not None:
        # Salva o novo arquivo tratado
        output_file = f"{nome_arquivo_base}_TRATADO.parquet"
        df_final.to_parquet(output_file, index=False)
        print(f"\nArquivo exportado com sucesso: {output_file}")
