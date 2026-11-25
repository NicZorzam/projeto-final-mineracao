"""
06_descrever_base.py — Mineração de Dados 2026.2 (Sprint 3): descreve a base final (metadados para o texto)
Entrada: Sprints/base_final/reviews_aaa_*.parquet  ->  Saída: Sprints/base_final/descricao_base.json
Uso (na pasta Sprints\\codigo):  py 06_descrever_base.py
"""
import glob, json, os, time
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BF = os.path.join(BASE, 'base_final')
COLS = ['user_id', 'game_id', 'is_positive', 'language', 'reviewed_at', 'playtime_at_review_h', 'votes_up',
        'votes_funny', 'num_games_owned', 'num_reviews', 'review_len', 'texto_vazio', 'steam_purchase',
        'received_for_free', 'written_during_early_access', 'primarily_steam_deck', 'votes_funny_overflow']
BINS = [-1, 1, 5, 20, 50, 100, 500, 1e12]
LAB = ['<1h', '1-5h', '5-20h', '20-50h', '50-100h', '100-500h', '500h+']


def add(acc, key, df):
    acc.setdefault(key, []).append(df)


def main():
    t0 = time.time()
    files = sorted(glob.glob(os.path.join(BF, 'reviews_aaa_*.parquet')))
    acc, users, lens = {}, [], []
    nulls = {}; n = 0; tmin = None; tmax = None
    schema = pq.read_schema(files[0])
    cols = [c for c in COLS if c in schema.names]
    for f in files:
        pf = pq.ParquetFile(f)
        for b in pf.iter_batches(batch_size=500_000, columns=cols):
            d = b.to_pandas()
            n += len(d)
            for c in d.columns: nulls[c] = nulls.get(c, 0) + int(d[c].isna().sum())
            d['pos'] = d.is_positive.astype('int64')
            users.append(d.groupby('user_id')['pos'].agg(['size', 'sum']))
            d['ano'] = d.reviewed_at.dt.year
            d['pt_bin'] = pd.cut(d.playtime_at_review_h, BINS, labels=LAB).astype(str)
            for k in ['language', 'ano', 'pt_bin', 'steam_purchase', 'received_for_free',
                      'written_during_early_access', 'primarily_steam_deck', 'texto_vazio']:
                if k in d: add(acc, k, d.groupby(k)['pos'].agg(['size', 'sum']))
            if 'votes_up' in d: add(acc, 'votos_up_bin', d.groupby(pd.cut(d.votes_up, [-1, 0, 1, 10, 100, 1e12]).astype(str))['pos'].agg(['size', 'sum']))
            lens.append(d.review_len.sample(min(len(d), 20000), random_state=0).to_numpy())
            mn, mx = d.reviewed_at.min(), d.reviewed_at.max()
            tmin = mn if tmin is None or mn < tmin else tmin
            tmax = mx if tmax is None or mx > tmax else tmax
        print(os.path.basename(f), f'{n:,}', round(time.time() - t0), 's', flush=True)
    out = {'reviews': n, 'arquivos': len(files),
           'tamanho_mb': round(sum(os.path.getsize(f) for f in files) / 1e6),
           'reviewed_at_min': str(tmin), 'reviewed_at_max': str(tmax), 'nulos': nulls}
    for k, v in acc.items():
        g = pd.concat(v).groupby(level=0).sum()
        out[k] = {str(i): {'n': int(a), 'pos': int(b)} for i, (a, b) in g.iterrows()}
    u = pd.concat(users).groupby(level=0).sum()
    out['usuarios'] = int(len(u))
    out['pos_total'] = int(u['sum'].sum())
    faixas = pd.cut(u['size'], [0, 1, 2, 4, 9, 49, 1e12], labels=['1', '2', '3-4', '5-9', '10-49', '50+'])
    fx = u.groupby(faixas, observed=False).agg(usuarios=('size', 'size'), reviews=('size', 'sum'), pos=('sum', 'sum'))
    out['usuarios_por_faixa'] = {str(i): {k: int(r[k]) for k in fx.columns} for i, r in fx.iterrows()}
    out['usuarios_top5'] = [{'user_id': int(i), 'reviews': int(r['size']), 'pos': int(r['sum'])} for i, r in u.nlargest(5, 'size').iterrows()]
    out['reviews_por_usuario_quantis'] = {str(q): float(u['size'].quantile(q)) for q in [.5, .75, .9, .99, .999]}
    L = np.concatenate(lens)
    out['review_len_quantis_amostra'] = {str(q): float(np.quantile(L, q)) for q in [.1, .25, .5, .75, .9, .99]}
    out['segundos'] = round(time.time() - t0)
    json.dump(out, open(os.path.join(BF, 'descricao_base.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK', n, 'reviews,', out['usuarios'], 'usuarios')


if __name__ == '__main__':
    main()
