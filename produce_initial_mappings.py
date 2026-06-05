import os
import re
import json


def carregar_dicionario_cnv(caminho_cnv):
    """Lê um arquivo .cnv do DATASUS e retorna um dicionário de mapeamento.

    Suporta linhas com comentários (;), múltiplos espaços e códigos simples ou
    faixas.
    """
    mapeamento = {}
    if not os.path.exists(caminho_cnv):
        print(f"Aviso: Arquivo de conversão não encontrado: {caminho_cnv}")
        return mapeamento

    with open(caminho_cnv, "r", encoding="latin-1") as f:
        f.readline()
        for linha in f:
            linha_limpa = linha.strip()

            if not linha_limpa or linha_limpa.startswith(";"):
                continue

            # 1. Regex ultra simples: Separa apenas o primeiro código de TODO o resto da linha
            match_base = re.match(r"^(\S+)\s+(.+)$", linha_limpa)
            if not match_base:
                continue

            p_codigo = match_base.group(1)
            resto_da_linha = match_base.group(2).strip()

            # 2. Verifica se o final da linha termina com a estrutura de chaves do Caso 2
            # Procura por uma sequência de números, hífens, vírgulas e espaços isolada no fim
            match_caso2 = re.search(
                r"\s{2,}([\d\-,\sMF]+)$", resto_da_linha
            )  # Modificado para aceitar espaços entre vírgulas

            if match_caso2:
                # O Caso 2 foi detectado
                bloco_chaves = match_caso2.group(1).strip()
                # A descrição é tudo que antecede o bloco de chaves mapeado
                descricao = resto_da_linha[: match_caso2.start()].strip()

                # Remove o código do IBGE/padrão que fica grudado no início da descrição
                if('-' not in descricao):
                    descricao = re.sub(r"^\d{3,}\s+", "", descricao)
            else:
                # Caso 1: Arquivos simples (a chave é o primeiro código)
                bloco_chaves = p_codigo
                descricao = resto_da_linha

            # 3. TRATAMENTO DE LISTAS E FAIXAS (Trata inclusive elementos nulos como ',   ,')
            # Divide pelas vírgulas
            partes_chaves = bloco_chaves.split(",")

            for parte in partes_chaves:
                parte = parte.strip()

                # Se a parte estiver vazia (ex: entre duas vírgulas com espaços), apenas ignora
                if not parte:
                    continue

                # Adiciona a versão sem zeros à esquerda se for string
                mapeamento[str(parte).lstrip("0") or "0"] = (
                    descricao
                )

    return mapeamento


def popular_config_mappings(diretorio_cnv, target_key="mamografias", config_file="config.json", mappings_source="cnv_mappings.json"):
    # 1. Carrega as definições de quais CNVs usar para cada coluna
    if not os.path.exists(mappings_source):
        print(f"Erro: Arquivo de origem de mapeamentos não encontrado: {mappings_source}")
        return

    with open(mappings_source, "r", encoding="utf-8") as f:
        cnv_mappings_def = json.load(f)

    if target_key not in cnv_mappings_def:
        print(f"Erro: Chave '{target_key}' não encontrada no arquivo de origem '{mappings_source}'.")
        return

    colunas_e_cnvs = cnv_mappings_def[target_key]

    # 2. Carrega o config.json atual (ou cria um novo se não existir)
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            try:
                config_data = json.load(f)
            except json.JSONDecodeError:
                config_data = {}
    else:
        config_data = {}

    # Garante a estrutura básica para a chave alvo
    if target_key not in config_data:
        config_data[target_key] = {"columns_to_drop": [], "mappings": {}}
    
    if "mappings" not in config_data[target_key]:
        config_data[target_key]["mappings"] = {}

    # 3. Gera os mapeamentos lendo os arquivos .cnv
    print(f"Gerando mapeamentos para '{target_key}' a partir dos arquivos .cnv...")
    for coluna, nome_cnv in colunas_e_cnvs.items():
        # Busca o arquivo ignorando case (ex: .CNV ou .cnv)
        caminho_completo_cnv = os.path.join(diretorio_cnv, nome_cnv)

        # Fallback caso o arquivo esteja com extensão minúscula no disco
        if not os.path.exists(caminho_completo_cnv):
            caminho_completo_cnv = os.path.join(
                diretorio_cnv, nome_cnv.lower()
            )
        
        # Fallback caso o arquivo original tenha sido passado em minúsculo mas esteja em maiúsculo
        if not os.path.exists(caminho_completo_cnv):
            caminho_completo_cnv = os.path.join(
                diretorio_cnv, nome_cnv.upper()
            )

        if os.path.exists(caminho_completo_cnv):
            dicionario_conversao = carregar_dicionario_cnv(caminho_completo_cnv)
            if dicionario_conversao:
                config_data[target_key]["mappings"][coluna] = dicionario_conversao
                print(f"  -> Mapeamento para '{coluna}' (usando {nome_cnv}) gerado com sucesso.")
        else:
            print(f"  -> Aviso: Arquivo CNV '{nome_cnv}' para a coluna '{coluna}' não encontrado em {diretorio_cnv}.")

    # 4. Salva o config.json atualizado
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)
    
    print(f"\nConfiguração para '{target_key}' salva com sucesso em '{config_file}'!")


# --- Execução ---
if __name__ == "__main__":
    import sys

    # Defaults
    diretorio_dos_cnvs = r"C:\Users\joaoo\Desktop\TAB_SISCAN"
    objeto_alvo = "mamografias_atend"

    # Se argumentos forem passados via CLI
    if len(sys.argv) > 1:
        diretorio_dos_cnvs = sys.argv[1]
    if len(sys.argv) > 2:
        objeto_alvo = sys.argv[2]
    
    popular_config_mappings(diretorio_dos_cnvs, objeto_alvo)
