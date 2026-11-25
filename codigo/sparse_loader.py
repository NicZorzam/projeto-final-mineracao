import sys, zipfile, os, io
import pyarrow.parquet as pq, pyarrow as pa
base=os.path.expanduser('~/mnt/Mineração/Sprints')
def load(name, cols):
    z=zipfile.ZipFile(os.path.join(base,'archive.zip'))
    size=z.getinfo(name).file_size
    TAIL=4<<20
    class Sparse(io.RawIOBase):
        def __init__(s,segs,size): s.segs=segs; s.size=size; s.pos=0
        def readable(s): return True
        def seekable(s): return True
        def tell(s): return s.pos
        def seek(s,o,w=0):
            s.pos = o if w==0 else (s.pos+o if w==1 else s.size+o); return s.pos
        def read(s,n=-1):
            if n<0: n=s.size-s.pos
            n=min(n,s.size-s.pos)
            for st,b in s.segs:
                if st<=s.pos and s.pos+n<=st+len(b):
                    r=b[s.pos-st:s.pos-st+n]; s.pos+=n; return bytes(r)
            raise IOError(f'range not loaded {s.pos} {n}')
        def readinto(s,buf):
            d=s.read(len(buf)); buf[:len(d)]=d; return len(d)
    # pass1 tail
    with z.open(name) as src:
        src.seek(size-TAIL)  # ZipExtFile seek decompresses forward
        tail=src.read()
    meta=pq.ParquetFile(pa.PythonFile(Sparse([(size-TAIL,tail)],size),mode='r')).metadata
    _unused=['game_id','is_positive','language','reviewed_at','playtime_at_review','votes_up','votes_funny','steam_purchase','received_for_free','written_during_early_access','primarily_steam_deck']
    names=[meta.schema.column(i).name for i in range(meta.num_columns)]
    ranges=[]
    for rg in range(meta.num_row_groups):
        r=meta.row_group(rg)
        for i,nm in enumerate(names):
            if nm in cols:
                c=r.column(i)
                st=c.dictionary_page_offset if c.has_dictionary_page and c.dictionary_page_offset else c.data_page_offset
                ranges.append((st,st+c.total_compressed_size))
    ranges.sort()
    # merge
    mr=[]
    for a,b in ranges:
        if mr and a<=mr[-1][1]+65536: mr[-1][1]=max(mr[-1][1],b)
        else: mr.append([a,b])
    segs=[]; pos=0; k=0
    with z.open(name) as src:
        cur=None
        while k<len(mr):
            a,b=mr[k]
            if pos<a:
                skip=a-pos
                while skip>0:
                    d=src.read(min(skip,16<<20)); skip-=len(d); pos+=len(d)
            buf=bytearray()
            while pos<b:
                d=src.read(min(b-pos,16<<20)); buf+=d; pos+=len(d)
            segs.append((a,buf)); k+=1
    segs.append((size-TAIL,tail))
    return pq.ParquetFile(pa.PythonFile(Sparse(segs,size),mode='r'))
