import json,glob,os,zipfile,io
import pandas as pd, numpy as np, pyarrow.parquet as pq
fs=sorted(glob.glob('agg/*.json'))
A={}; N=0; nulls={}; ovf=0
for f in fs:
    d=json.load(open(f)); N+=d['n']; ovf+=d['funny_ovf']
    for k,v in d['nulls'].items(): nulls[k]=nulls.get(k,0)+v
    for k,m in d['agg'].items():
        for kk,(a,b) in m.items():
            A.setdefault(k,{}).setdefault(kk,[0,0]); A[k][kk][0]+=a; A[k][kk][1]+=b
S={'n_reviews':N,'n_files':len(fs),'nulls':nulls,'funny_ovf':ovf}
pos=sum(v[1] for v in A['year'].values()); S['pos_rate']=pos/N
for k in A:
    if k=='game': continue
    S[k]={kk:{'n':a,'pos':b/a if a else None} for kk,(a,b) in A[k].items()}
g=pd.DataFrame([(int(k),a,b) for k,(a,b) in A['game'].items()],columns=['game_id','n','pos'])
S['n_games_with_reviews']=len(g)
S['reviews_per_game_q']=g.n.quantile([.5,.75,.9,.99]).to_dict(); S['reviews_per_game_max']=int(g.n.max())
z=zipfile.ZipFile(os.path.expanduser('~/mnt/Mineração/Sprints/archive.zip'))
games=pq.read_table(io.BytesIO(z.read('games.parquet'))).to_pandas()
tags=pq.read_table(io.BytesIO(z.read('game_tags.parquet'))).to_pandas()
S['n_games']=len(games); S['n_games_tags']=len(tags)
S['games_free']=float(games.game_is_free.mean()); S['games_coming_soon']=int(games.game_coming_soon.sum())
S['price_q']=games.game_price.describe().to_dict()
S['games_nulls']=games.isna().sum().to_dict()
gg=games.merge(g,on='game_id',how='left')
S['games_no_reviews']=int(gg.n.isna().sum())
S['orphan_review_games']=int((~g.game_id.isin(games.game_id)).sum())
ex=gg.dropna(subset=['n']).explode('game_genres')
gen=ex.groupby('game_genres').agg(games=('game_id','nunique'),n=('n','sum'),pos=('pos','sum'))
gen['rate']=gen.pos/gen.n
S['genres']=gen.sort_values('n',ascending=False).head(15).reset_index().to_dict('records')
tg=tags.explode('tag_names').tag_names.value_counts().head(20)
S['top_tags']=tg.to_dict(); S['n_unique_tags']=int(tags.explode('tag_names').tag_names.nunique())
gg['free']=gg.game_is_free
pr=gg.dropna(subset=['n']).copy()
pr['pb']=pd.cut(pr.game_price.fillna(0),[-1,0,5,15,30,60,1e6],labels=['Grátis/0','≤5','5-15','15-30','30-60','>60']).astype(str)
p=pr.groupby('pb').agg(games=('game_id','size'),n=('n','sum'),pos=('pos','sum')); p['rate']=p.pos/p.n
S['price_bins']=p.reset_index().to_dict('records')
S['top_games']=pr.sort_values('n',ascending=False).head(10)[['game_name','n','pos']].assign(rate=lambda x:x.pos/x.n).to_dict('records')
rd=pd.to_datetime(games.game_release_date,errors='coerce'); S['release_parsed']=float(rd.notna().mean()); S['release_range']=[str(rd.min()),str(rd.max())]
S['release_sample']=games.game_release_date.head(5).tolist()
json.dump(S,open(os.path.expanduser('~/mnt/Mineração/Sprints/sprint1_resumo_dataset.json'),'w'),ensure_ascii=False,indent=1,default=str)
print(json.dumps({k:S[k] for k in ['n_reviews','pos_rate','n_games','n_games_with_reviews','games_no_reviews','orphan_review_games','funny_ovf','nulls','release_range','release_parsed','reviews_per_game_q','price_q']},default=str,indent=0))
