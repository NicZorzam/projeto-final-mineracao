"""
03_reviews_por_jogo.py  —  Mineração de Dados 2026.2 (Sprint 3)

Gera, a partir de Sprints/archive.zip, sem extrair os parquet de reviews:
  dados_derivados/games.parquet            (copiado do zip)
  dados_derivados/game_tags.parquet        (copiado do zip)
  dados_derivados/reviews_por_jogo_idioma.csv   game_id, language, n, pos
  dados_derivados/log_03.json              tempos e contagens por arquivo

Leitura "esparsa": lê o rodapé de cada parquet dentro do zip e descomprime
apenas os column chunks de game_id, is_positive e language.

Uso (na pasta Sprints\\codigo):  python 03_reviews_por_jogo.py
Requisitos: Python 3.9+, pyarrow, pandas  (pip install pyarrow pandas)
"""
import io, json, os, sys, time, zipfile
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # ...\Sprints
ZIP = os.path.join(BASE, 'archive.zip')
OUT = os.path.join(BASE, 'dados_derivados')
COLS = ['game_id', 'is_positive', 'language']
TAIL = 4 << 20


class Sparse(io.RawIOBase):
    def __init__(s, segs, size): s.segs, s.size, s.pos = segs, size, 0
    def readable(s): return True
    def seekable(s): return True
    def tell(s): return s.pos
    def seek(s, o, w=0):
        s.pos = o if w == 0 else (s.pos + o if w == 1 else s.size + o); return s.pos
    def read(s, n=-1):
        if n < 0: n = s.size - s.pos
        n = min(n, s.size - s.pos)
        for st, b in s.segs:
            if st <= s.pos and s.pos + n <= st + len(b):
                r = b[s.pos - st:s.pos - st + n]; s.pos += n; return bytes(r)
        raise IOError(f'faixa nao carregada {s.pos} {n}')
    def readinto(s, buf):
        d = s.read(len(buf)); buf[:len(d)] = d; return len(d)


def sparse_parquet(z, name, cols):
    size = z.getinfo(name).file_size
    tail_start = max(0, size - TAIL)
    with z.open(name) as src:
        src.seek(tail_start)
        tail = src.read()
    meta = pq.ParquetFile(pa.PythonFile(Sparse([(tail_start, tail)], size), mode='r')).metadata
    names = [meta.schema.column(i).name for i in range(meta.num_columns)]
    ranges = []
    for rg in range(meta.num_row_groups):
        r = meta.row_group(rg)
        for i, nm in enumerate(names):
            if nm in cols:
                c = r.column(i)
                st = c.dictionary_page_offset if c.has_dictionary_page and c.dictionary_page_offset else c.data_page_offset
                ranges.append((st, st + c.total_compressed_size))
    ranges.sort()
    mr = []
    for a, b in ranges:
        if mr and a <= mr[-1][1] + 65536: mr[-1][1] = max(mr[-1][1], b)
        else: mr.append([a, b])
    segs, pos = [], 0
    with z.open(name) as src:
        for a, b in mr:
            while pos < a:
                d = src.read(min(a - pos, 16 << 20)); pos += len(d)
            buf = bytearray()
            while pos < b:
                d = src.read(min(b - pos, 16 << 20)); buf += d; pos += len(d)
            segs.append((a, buf))
    segs.append((tail_start, tail))
    return pq.ParquetFile(pa.PythonFile(Sparse(segs, size), mode='r'))


def main():
    os.makedirs(OUT, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    members = z.namelist()
    log = {'inicio': time.strftime('%Y-%m-%d %H:%M:%S'), 'arquivos': []}

    # 1) games.parquet e game_tags.parquet (pequenos): copia direto
    for want in ('games.parquet', 'game_tags.parquet'):
        m = [x for x in members if os.path.basename(x) == want]
        if not m: print('AVISO: nao achei', want); continue
        dst = os.path.join(OUT, want)
        with z.open(m[0]) as src, open(dst, 'wb') as fh:
            while True:
                d = src.read(16 << 20)
                if not d: break
                fh.write(d)
        print('copiado', want, os.path.getsize(dst) // 1_000_000, 'MB')

    # 2) reviews: contagem por (game_id, language)
    rev = sorted(x for x in members if os.path.basename(x).startswith('reviews-') and x.endswith('.parquet'))
    print(len(rev), 'arquivos de reviews')
    acc = []
    total = 0
    for name in rev:
        t0 = time.time()
        f = sparse_parquet(z, name, COLS)
        parts = []
        for i in range(f.num_row_groups):
            d = f.read_row_group(i, columns=COLS).to_pandas()
            d['pos'] = d.is_positive.astype('int64')
            d['language'] = d.language.astype(str)
            parts.append(d.groupby(['game_id', 'language'])['pos'].agg(n='size', pos='sum'))
        g = pd.concat(parts).groupby(level=[0, 1]).sum()
        n = int(g['n'].sum()); total += n
        acc.append(g)
        dt = round(time.time() - t0)
        log['arquivos'].append({'arquivo': name, 'reviews': n, 'segundos': dt})
        print(f'{name}: {n:,} reviews em {dt}s (acumulado {total:,})', flush=True)

    res = pd.concat(acc).groupby(level=[0, 1]).sum().reset_index()
    res.to_csv(os.path.join(OUT, 'reviews_por_jogo_idioma.csv'), index=False)
    log['total_reviews'] = total
    log['linhas_csv'] = len(res)
    log['fim'] = time.strftime('%Y-%m-%d %H:%M:%S')
    log['versoes'] = {'python': sys.version.split()[0], 'pandas': pd.__version__, 'pyarrow': pa.__version__}
    json.dump(log, open(os.path.join(OUT, 'log_03.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('OK. Total:', f'{total:,}', '(esperado 121.312.346)')


if __name__ == '__main__':
    main()
