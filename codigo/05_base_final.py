"""
05_base_final.py  —  Mineração de Dados 2026.2 (Sprint 3): gera a BASE FINAL (reviews de jogos AAA, critério C4)

Critério C4 (adotado): jogo publicado por uma das 17 publicadoras da lista do VideoGamesCritic (2026)
OU por Koei Tecmo, Paradox ou Larian (ampliação do grupo); jogos com a tag Indie NÃO são excluídos.
A lista vem de dados_derivados/jogos_aaa_selecionados.csv, gerada por 04_criterios_aaa.py.

Entradas : Sprints/archive.zip ; Sprints/dados_derivados/{games,game_tags}.parquet, jogos_aaa_selecionados.csv
Saídas   : Sprints/base_final/
             reviews_aaa_000.parquet ... reviews_aaa_012.parquet   (uma parte por arquivo original)
             jogos_aaa.parquet                                     (metadados dos 1.527 jogos)
             log_05.json                                           (contagens de cada tratamento)
Temporário: Sprints/_tmp_05/ (um parquet de ~2 GB por vez; apagado ao fim de cada arquivo)

Tratamentos (justificativas no texto do Sprint 3):
  T1 filtro C4 por game_id
  T2 votes_funny = 4.294.967.295 (estouro de inteiro 32 bits) -> nulo  [flag votes_funny_overflow]
  T3 playtime_at_review nulo mantido nulo; coluna derivada playtime_at_review_h (horas)
  T4 texto vazio/nulo sinalizado [flag texto_vazio]; comprimento do texto em caracteres [review_len]
  T5 duplicatas de review_id verificadas (contadas no log)
  T6 jogos: data de lançamento em texto -> data; anos < 1970 ou > 2030 viram nulo (1969 e 2104 são placeholders); "Coming soon"/"To be announced" ficam nulos
Uso (na pasta Sprints\\codigo):  py 05_base_final.py
"""
import json, os, shutil, sys, time, zipfile
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP = os.path.join(BASE, 'archive.zip')
DER = os.path.join(BASE, 'dados_derivados')
OUT = os.path.join(BASE, 'base_final')
TMP = os.path.join(BASE, '_tmp_05')
OVF = 4294967295


def jogos_aaa():
    c1 = pd.read_csv(os.path.join(DER, 'jogos_aaa_selecionados.csv'))
    ids = set(c1['game_id'].astype('int64'))
    g = pd.read_parquet(os.path.join(DER, 'games.parquet'))
    t = pd.read_parquet(os.path.join(DER, 'game_tags.parquet'))
    g = g[g.game_id.isin(ids)].copy()
    g = g.merge(c1[['game_id', 'grupos', 'origem']].rename(columns={'grupos': 'grupo_publicadora', 'origem': 'origem_criterio'}), on='game_id', how='left')
    d = pd.to_datetime(g.game_release_date, format='%b %d, %Y', errors='coerce')
    d2 = pd.to_datetime(g.game_release_date, format='%d %b, %Y', errors='coerce')
    d = d.fillna(d2)
    d[(d.dt.year < 1970) | (d.dt.year > 2030)] = pd.NaT
    g['release_date'] = d
    g = g.merge(t[['game_id', 'tag_names', 'tag_weights']], on='game_id', how='left')
    g = g.drop(columns=['game_header_image'])
    return ids, g


def main():
    t_ini = time.time()
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    ids, g = jogos_aaa()
    g.to_parquet(os.path.join(OUT, 'jogos_aaa.parquet'), index=False)
    print(f'{len(g)} jogos AAA (C4); datas de lançamento não convertidas: {int(g.release_date.isna().sum())}')
    id_arr = pa.array(sorted(ids), type=pa.int64())

    z = zipfile.ZipFile(ZIP)
    rev = sorted(x for x in z.namelist() if os.path.basename(x).startswith('reviews-') and x.endswith('.parquet'))
    log = {'inicio': time.strftime('%Y-%m-%d %H:%M:%S'), 'jogos_aaa': len(g), 'arquivos': []}
    all_ids = []
    tot = {'lidas': 0, 'aaa': 0, 'funny_ovf': 0, 'pt_nulo': 0, 'texto_vazio': 0}
    for name in rev:
        t0 = time.time()
        tmp = os.path.join(TMP, os.path.basename(name))
        with z.open(name) as src, open(tmp, 'wb') as fh:
            shutil.copyfileobj(src, fh, 16 << 20)
        f = pq.ParquetFile(tmp)
        dst = os.path.join(OUT, os.path.basename(name).replace('reviews-', 'reviews_aaa_'))
        w = None; st = {'arquivo': name, 'lidas': 0, 'aaa': 0, 'funny_ovf': 0, 'pt_nulo': 0, 'texto_vazio': 0}
        for b in f.iter_batches(batch_size=200_000):
            tb = pa.Table.from_batches([b]); st['lidas'] += tb.num_rows
            gid = pc.cast(tb['game_id'], pa.int64())
            tb = tb.filter(pc.is_in(gid, value_set=id_arr))
            if tb.num_rows == 0: continue
            vf = tb['votes_funny']
            ovf = pc.equal(pc.cast(vf, pa.int64()), OVF)
            tb = tb.set_column(tb.schema.get_field_index('votes_funny'), 'votes_funny',
                               pc.if_else(ovf, pa.scalar(None, vf.type), vf))
            tb = tb.append_column('votes_funny_overflow', pc.fill_null(ovf, False))
            pt = tb['playtime_at_review']
            tb = tb.append_column('playtime_at_review_h', pc.divide(pc.cast(pt, pa.float64()), 60.0))
            txt = pc.utf8_trim_whitespace(pc.fill_null(tb['review'], ''))
            ln = pc.utf8_length(txt)
            tb = tb.append_column('review_len', pc.cast(ln, pa.int32()))
            tb = tb.append_column('texto_vazio', pc.equal(ln, 0))
            st['aaa'] += tb.num_rows
            st['funny_ovf'] += int(pc.sum(pc.cast(pc.fill_null(ovf, False), pa.int64())).as_py() or 0)
            st['pt_nulo'] += pt.null_count
            st['texto_vazio'] += int(pc.sum(pc.cast(tb['texto_vazio'], pa.int64())).as_py() or 0)
            all_ids.append(pc.cast(tb['review_id'], pa.int64()).to_numpy())
            if w is None:
                w = pq.ParquetWriter(dst, tb.schema, compression='zstd')
            w.write_table(tb.cast(w.schema))
        if w: w.close()
        del f
        os.remove(tmp)
        st['segundos'] = round(time.time() - t0)
        st['mb_saida'] = round(os.path.getsize(dst) / 1e6) if os.path.exists(dst) else 0
        for k in tot: tot[k] += st[k]
        log['arquivos'].append(st)
        print(f"{name}: {st['lidas']:,} lidas -> {st['aaa']:,} AAA ({st['mb_saida']} MB) em {st['segundos']}s | acumulado AAA {tot['aaa']:,}", flush=True)

    ids_all = np.concatenate(all_ids) if all_ids else np.array([], dtype=np.int64)
    u = np.unique(ids_all)
    tot['review_id_duplicados'] = int(len(ids_all) - len(u))
    log['totais'] = tot
    log['fim'] = time.strftime('%Y-%m-%d %H:%M:%S'); log['minutos'] = round((time.time() - t_ini) / 60, 1)
    log['versoes'] = {'python': sys.version.split()[0], 'pandas': pd.__version__, 'pyarrow': pa.__version__, 'numpy': np.__version__}
    json.dump(log, open(os.path.join(OUT, 'log_05.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    try: os.rmdir(TMP)
    except OSError: pass
    print('OK.', tot, '(esperado AAA = 29.573.250)')


if __name__ == '__main__':
    main()
