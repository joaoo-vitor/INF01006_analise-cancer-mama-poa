# Analise de Dados de 2024 de Câncer de Mama e Colo de Útero em Porto Alegre e no Rio Grande do Sul

## Convertendo os dados
Para que possamos analisar os dados dos exames, temos que decodificar os valores das tabelas usando o arquivo de definição (".def") do SISCAN.
Temos o seguinte mapeamento das base de dados para os arquivos de definição presentes nos arquivos de tabulação do SISCAN:
-*"mamografia.def"*: usado na conversão das tabelas de mamografias "SISCAN_MAMOGRAFIA_<ano>.csv" e "SISCAN_MAMOGRAFIA_PACNT_<ano>.csv"
-*"cito_mama.def"*: usado na conversão das tabelas de exames citopatológicos de mama "SISCAN_CITO_MAMA_PACNT_<ano>.csv" e "SISCAN_CITO_MAMA_<ano>.csv".
-*"histo_mama.def"*: usado na conversão das tabelas de exames histopatológicos de mama "SISCSAN_HISTO_MAMA_PACNT_<ano>.csv" e "SISCAN_HISTO_MAMA_<ano>.csv"

Para converter uma base de dados de mamografia, utilize
```
python convert_mamografia.py <caminho_arquivo_csv> <caminho_arquivo_def>
```

Para converter uma base de dados de exames citopatológicos de mama, utilize
```
python convert_cito_mama.py <caminho_arquivo_csv> <caminho_arquivo_def>
```

Para converter uma base de dados de exames histopatológicos de mama, utilize
```
python convert_histo_mama.py <caminho_arquivo_csv> <caminho_arquivo_def>
```

## Arquitetura
Após conversão dos dados, os dados são guardados em arquivo parquet, para que possam ser lidos pelo Servidor Web que hospeda os gráficos. Será possível visualizá-los usando o dashboard Streamlit.
