import sys, zipfile, json, os, time, io
import pyarrow.parquet as pq, pyarrow as pa
import pandas as pd, numpy as np
name=sys.argv[1]
base=os.path.expanduser('~/mnt/Mineração/Sprints')
t0=time.time()
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
cols=['game_id','is_positive','language','reviewed_at','playtime_at_review','votes_up','votes_funny','steam_purchase','received_for_free','written_during_early_access','primarily_steam_deck']
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
t1=time.time()
f=pq.ParquetFile(pa.PythonFile(Sparse(segs,size),mode='r'))
acc={}
def add(key,s): acc.setdefault(key,[]).append(s)
nulls={}; n=0; funny_ovf=0
for i in range(f.num_row_groups):
    t=f.read_row_group(i,columns=cols)
    for c in t.column_names: nulls[c]=nulls.get(c,0)+t[c].null_count
    d=t.to_pandas(); n+=len(d)
    funny_ovf+=int((d.votes_funny>=4294967295).sum())
    d['pos']=d.is_positive.astype(int); d['year']=d.reviewed_at.dt.year
    pt=d.playtime_at_review/60
    d['pt_bin']=pd.cut(pt,[-1,1,5,20,50,100,500,1e9],labels=['<1h','1-5h','5-20h','20-50h','50-100h','100-500h','500h+']).astype(str)
    for k2 in ['language','year','pt_bin','written_during_early_access','received_for_free','steam_purchase','primarily_steam_deck']:
        add(k2,d.groupby(k2)['pos'].agg(['size','sum']))
    add('game',d.groupby('game_id')['pos'].agg(['size','sum']))
    add('vu',d.groupby(pd.cut(d.votes_up,[-1,0,1,10,100,1e12]).astype(str))['pos'].agg(['size','sum']))
out={'file':name,'n':n,'nulls':nulls,'funny_ovf':funny_ovf,'loaded_mb':sum(len(b) for _,b in segs)/1e6,'t_stream':t1-t0,'t_total':time.time()-t0}
res={}
for k2,v in acc.items():
    g=pd.concat(v).groupby(level=0).sum()
    res[k2]={str(i):[int(a),int(b)] for i,(a,b) in g.iterrows()}
out['agg']=res
json.dump(out,open(os.path.expanduser(f'~/work/agg/{name}.json'),'w'))
print(name,n,round(out['loaded_mb']),round(t1-t0),round(time.time()-t0))
