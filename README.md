# O que os jogadores dizem sobre jogos AAA: mineração de reviews da Steam

Projeto final de **Mineração de Dados 2026.2** (IC/UFRJ, Prof. Silas Lima Filho).
Grupo: Nicolly Zorzam Moura (DRE 121037550) e Pedro Jorge Câmara (DRE 126068409).

Repositório: https://github.com/NicZorzam/projeto-final-mineracao

## Dados

- **Original:** [Steam Reviews, Games and Tags](https://www.kaggle.com/datasets/sergiodelcarpio/steam-reviews), de Sergio Del Carpio. É a versão 1 no Kaggle, um snapshot de 30/10/2026 (UTC), coletado da Steam Web API pelo pipeline [steam-recsys-e2e](https://github.com/sadelcarpio/steam-recsys-e2e). Tem 121.312.346 reviews, 184.885 jogos e 429 tags, em um `archive.zip` de 23,3 GB. Pelos termos do dataset, os textos pertencem aos seus autores, o uso é para pesquisa e educação, e a base não deve ser usada para identificar ou contatar avaliadores.
- **Base final:** 29.573.250 reviews de 1.527 jogos AAA, em 5,8 GB de Parquet. Está no Google Drive: **[LINK]**. O dicionário de dados está em [`base_final/DICIONARIO_DE_DADOS.md`](base_final/DICIONARIO_DE_DADOS.md).
- **Critério de AAA (C4):** o jogo é publicado por uma das 17 publicadoras da lista do [VideoGamesCritic](https://videogamescritic.com/findings/did-aaa-games-get-worse) ou por Koei Tecmo, Paradox ou Larian, que foram acrescentadas pelo grupo. Jogos com a tag Indie não são excluídos.

Os arquivos grandes (`archive.zip` e todos os `.parquet`) ficam fora do Git; veja o `.gitignore`.

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `codigo/` | scripts do pipeline (ver abaixo) |
| `dados_derivados/` | arquivos gerados a partir do zip original: contagem de reviews por jogo × idioma, comparação dos critérios de AAA, lista dos jogos selecionados, mapeamento das grafias de publicadoras, classificação de publicadoras do Video Game Insights (consultada em 25/11/2026) e resumos da Sprint 1 |
| `base_final/` | dicionário de dados, log dos tratamentos (`log_05.json`) e estatísticas descritivas (`descricao_base.json`); os `.parquet` ficam no Drive |
| `artigo/` | texto no modelo SBC (LaTeX), referências e PDF |
| `apresentacoes/` | slides das sprints em PDF |

## Como reproduzir

1. Instale o Python 3.12 e as dependências: `pip install -r requirements.txt`.
2. Baixe o `archive.zip` do Kaggle e coloque-o na **raiz** do repositório.
3. Dentro de `codigo/`, rode os scripts em ordem:

| Script | O que faz | Saída | Tempo* |
|---|---|---|---|
| `03_reviews_por_jogo.py` | copia `games` e `game_tags` e conta as reviews por jogo × idioma, sem extrair os parquet de reviews (leitura esparsa) | `dados_derivados/` | 6 min |
| `04_criterios_aaa.py` | compara os critérios de AAA e grava a lista final (C4) | `criterios_aaa.csv`, `jogos_aaa_selecionados.csv` | segundos |
| `05_base_final.py` | filtra os jogos do C4 e aplica os tratamentos | `base_final/reviews_aaa_*.parquet`, `jogos_aaa.parquet`, `log_05.json` | 6,9 min |
| `06_descrever_base.py` | calcula as estatísticas descritivas da base final | `base_final/descricao_base.json` | 2 min |

\* Tempos medidos em um PC com Windows 10 64 bits, AMD Ryzen 5 2400G, 16 GB de RAM e SSD.

Os scripts `01_agregar_reviews.py`, `02_consolidar_resumo.py`, `agg_users.py`, `merge_users.py` e `sparse_loader.py` são da varredura da Sprint 1, que rodou numa máquina virtual Linux. Eles ainda usam caminhos fixos dessa máquina; os resultados estão em `dados_derivados/sprint1_resumo_*.json`.
