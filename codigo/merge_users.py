import numpy as np, pandas as pd, glob, os, json, sys
d0=os.path.expanduser('~/mnt/Mineração/Sprints/_cache_usuarios')
dt=np.dtype([('u','<i8'),('n','<i4'),('pos','<i4'),('pt','<f4'),('nr','<i4')])
ps=[int(x) for x in sys.argv[1:]]
for p in ps:
    arrs=[np.fromfile(f,dtype=dt) for f in sorted(glob.glob(f'{d0}/p{p:02d}_*.bin'))]
    df=pd.DataFrame(np.concatenate(arrs)); del arrs
    g=df.groupby('u').agg(n=('n','sum'),pos=('pos','sum'),pt=('pt','sum'),nr=('nr','max')); del df
    g['rate']=g.pos/g.n
    nb=pd.cut(g.n,[0,1,2,4,9,19,49,1e9],labels=['1','2','3-4','5-9','10-19','20-49','50+']).astype(str)
    cls=np.where(g.pos==g.n,'sempre_pos',np.where(g.pos==0,'sempre_neg','misto'))
    R={}
    R['by_nbin']=g.groupby(nb).agg(users=('n','size'),reviews=('n','sum'),pos=('pos','sum'),rate_sum=('rate','sum')).to_dict('index')
    R['cls_by_nbin']=pd.crosstab(nb,cls).to_dict('index')
    ptm=g.pt/g.n
    pb=pd.cut(ptm,[-1,1,5,20,50,100,1e9],labels=['<1h','1-5h','5-20h','20-50h','50-100h','100h+']).astype(str)
    m=g.n>=5
    R['pt_users5']=g[m].groupby(pb[m]).agg(users=('n','size'),rate_sum=('rate','sum'),reviews=('n','sum'),pos=('pos','sum')).to_dict('index')
    R['rate_hist5']=np.histogram(g.rate[m],bins=10,range=(0,1))[0].tolist()
    R['users']=len(g); R['max_n']=int(g.n.max())
    json.dump(R,open(os.path.expanduser(f'~/work/agg/users_p{p:02d}.json'),'w'),default=int)
    print(p,len(g),flush=True)
