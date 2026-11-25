# Dicionário de dados — base final (Sprint 3)

Base: reviews da Steam de **jogos AAA**, segundo o critério **C4**: jogo de uma das 17 publicadoras da lista do VideoGamesCritic (2026) ou de Koei Tecmo, Paradox e Larian (acréscimo do grupo). Jogos com a tag "Indie" não são excluídos.
Gerada por `codigo/05_base_final.py` a partir de `archive.zip`. Formato: Parquet, compressão zstd.

| Arquivo | Linhas | Conteúdo |
|---|---|---|
| `reviews_aaa_000.parquet` … `reviews_aaa_012.parquet` | 29.573.250 no total | uma linha por review; cada parte vem de `reviews-000` … `reviews-012` do arquivo original |
| `jogos_aaa.parquet` | 1.527 | uma linha por jogo AAA (1.481 têm ao menos uma review) |
| `log_05.json` | — | contagens de cada tratamento, tempos e versões |
| `descricao_base.json` | — | estatísticas descritivas, geradas por `06_descrever_base.py` |

## reviews_aaa_*.parquet

| Campo | Tipo | Descrição | Origem |
|---|---|---|---|
| `review_id` | inteiro | identificador da review (sem duplicatas: verificado) | original |
| `user_id` | inteiro | identificador pseudônimo do autor: hash com chave (HMAC-SHA256, 63 bits) do SteamID64; estável entre versões e irreversível sem a chave | original |
| `game_id` | inteiro | identificador do jogo (chave para `jogos_aaa`) | original |
| `is_positive` | booleano | recomenda o jogo (verdadeiro) ou não | original |
| `review` | texto | texto livre da review | original |
| `language` | texto | idioma declarado (31 valores, ex.: `english`, `schinese`, `russian`, `brazilian`) | original |
| `reviewed_at` | data e hora | data da review (UTC) | original |
| `updated_at` | data e hora | data da última edição (UTC) | original |
| `playtime_forever` | inteiro (min) | minutos jogados no total | original |
| `playtime_last_two_weeks` | inteiro (min) | minutos jogados nas duas semanas antes da coleta | original |
| `playtime_at_review` | inteiro (min) | minutos jogados até a review; **nulo em 94.995** casos (mantido nulo) | original |
| `num_games_owned` | inteiro | jogos na biblioteca do autor; **nulo em 635.493** casos (mantido nulo) | original |
| `num_reviews` | inteiro | reviews escritas pelo autor na Steam (em todos os jogos) | original |
| `votes_up` | inteiro | votos de "útil" | original |
| `votes_funny` | inteiro | votos de "engraçado"; **198 valores 4.294.967.295 viraram nulos** (estouro de 32 bits) | tratado |
| `weighted_vote_score` | real | pontuação de utilidade calculada pela Steam | original |
| `comment_count` | inteiro | número de comentários na review | original |
| `steam_purchase` | booleano | jogo comprado na Steam | original |
| `received_for_free` | booleano | jogo recebido de graça | original |
| `written_during_early_access` | booleano | review escrita durante o acesso antecipado | original |
| `primarily_steam_deck` | booleano | autor jogou principalmente no Steam Deck | original |
| `votes_funny_overflow` | booleano | verdadeiro se `votes_funny` era o valor de estouro | derivado |
| `playtime_at_review_h` | real (h) | `playtime_at_review` / 60 | derivado |
| `review_len` | inteiro | nº de caracteres do texto, sem espaços nas pontas | derivado |
| `texto_vazio` | booleano | texto vazio ou só com espaços (**106.169** casos) | derivado |

## jogos_aaa.parquet

| Campo | Tipo | Descrição |
|---|---|---|
| `game_id`, `game_name` | inteiro, texto | jogo |
| `game_short_description` | texto | descrição curta da loja |
| `game_release_date` | texto | data de lançamento original, em texto (ex.: "Mar 27, 2018") |
| `release_date` | data | data convertida; nula se for inválida (ano < 1970 ou > 2030) ou um marcador ("Coming soon", "To be announced") |
| `game_is_free`, `game_price` | booleano, real | gratuito; preço **no momento da coleta** (moeda não documentada) |
| `game_developers`, `game_publishers` | listas | desenvolvedoras e publicadoras, como estão no dataset |
| `grupo_publicadora` | texto | publicadora(s) do critério, separadas por `;` (um jogo tem duas: Bandai Namco e Paradox) |
| `origem_criterio` | texto | `VideoGamesCritic` (1.320 jogos) ou `ampliacao` (207 jogos de Koei Tecmo, Paradox e Larian) |
| `game_genres`, `game_categories` | listas | gêneros e categorias da loja |
| `game_coming_soon` | booleano | jogo ainda não lançado |
| `tag_names`, `tag_weights` | listas | tags da comunidade e respectivos pesos (coletadas entre 29/09 e 29/10/2026) |

## Fora da base final

- 91.407.129 reviews de jogos que não são AAA pelo critério C4.
- 331.967 reviews cujo `game_id` não está cadastrado em `games`, já que sem cadastro não há publicadora.
