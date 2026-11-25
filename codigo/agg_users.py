import sys, os, time, numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa, zipfile
sys.argv=[sys.argv[0]]+sys.argv[1:]
exec(open(os.path.expanduser('~/work/sparse_loader.py')).read())
name=sys.argv[1]
t0=time.time()
f=load(name,['user_id','is_positive','playtime_at_review','num_reviews'])
out=os.path.expanduser('~/mnt/Mineração/Sprints/_cache_usuarios'); os.makedirs(out,exist_ok=True)
parts=[]
for i in range(f.num_row_groups):
    parts.append(f.read_row_group(i,columns=['user_id','is_positive','playtime_at_review','num_reviews']).to_pandas())
d=pd.concat(parts); del parts
d['pos']=d.is_positive.astype(np.int32); d['pt']=(d.playtime_at_review.fillna(0)/60).astype(np.float32)
g=d.groupby('user_id').agg(n=('pos','size'),pos=('pos','sum'),pt=('pt','sum'),nr=('num_reviews','max'))
del d
g=g.reset_index()
P=16
k=(g.user_id.values % P)
for p in range(P):
    s=g[k==p]
    arr=np.rec.fromarrays([s.user_id.values.astype(np.int64),s.n.values.astype(np.int32),s.pos.values.astype(np.int32),s.pt.values.astype(np.float32),s.nr.values.astype(np.int32)])
    with open(f'{out}/p{p:02d}_{name}.bin','wb') as fh: fh.write(arr.tobytes())
print(name,len(g),round(time.time()-t0))
