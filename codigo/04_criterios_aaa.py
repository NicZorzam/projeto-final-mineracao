"""04_criterios_aaa.py — conta jogos e reviews selecionados por cada critério de AAA e grava a lista final (C4 = C1 + Koei Tecmo, Paradox, Larian).
Entrada/saída: Sprints/dados_derivados (gerado pelo 03). Uso: py 04_criterios_aaa.py"""
import pandas as pd, numpy as np, json
import os, sys
D=sys.argv[1] if len(sys.argv)>1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"dados_derivados")+os.sep
g=pd.read_parquet(D+'games.parquet'); t=pd.read_parquet(D+'game_tags.parquet'); r=pd.read_csv(D+'reviews_por_jogo_idioma.csv')
PUB={ # nome no dataset -> grupo (lista VideoGamesCritic 2026)
 'Electronic Arts':'EA','Activision':'Activision','Activision (Excluding Japan and Asia)':'Activision','Activision Value Publishing Inc.':'Activision',
 'Blizzard Entertainment, Inc.':'Blizzard','Ubisoft':'Ubisoft','Ubisoft Entertainment':'Ubisoft','UBISOFT':'Ubisoft',
 '2K':'2K','2K Games':'2K','Rockstar Games':'Rockstar',
 'PlayStation Publishing LLC':'Sony','PlayStation Publishing LLC (excluding China)':'Sony',
 'Xbox Game Studios':'Xbox','Xbox Games Studios':'Xbox','Microsoft Studios':'Xbox','Microsoft Corporation':'Xbox',
 'Bethesda Softworks':'Bethesda','Bethesda Game Studios':'Bethesda',
 'Square Enix':'Square Enix',
 'CAPCOM Co., Ltd.':'Capcom','Capcom':'Capcom','CAPCOM CO., LTD':'Capcom','CAPCOM CO., LTD.':'Capcom','CAPCOM U.S.A., INC.':'Capcom','Capcom U.S.A, Inc.':'Capcom','CAPCOM':'Capcom','Capcom U.S.A., Inc.':'Capcom',
 'Bandai Namco Entertainment':'Bandai Namco','BANDAI NAMCO Entertainment':'Bandai Namco','Bandai Namco Entertainment Inc.':'Bandai Namco','BANDAI NAMCO Entertainment Europe':'Bandai Namco','BANDAI NAMCO Entertainment Inc.':'Bandai Namco','Bandai Namco Entertainment Europe':'Bandai Namco','Bandai Namco':'Bandai Namco','Bandai Namco Europe S.A.S.':'Bandai Namco','BANDAI NAMCO Entertainment America Inc.':'Bandai Namco','Bandai Namco Entertainment Asia':'Bandai Namco',
 'SEGA':'Sega','SEGA (Japan)':'Sega',
 'Warner Bros. Games':'Warner','Warner Bros. Interactive Entertainment':'Warner','WB Games':'Warner','Warner Bros. Interactive':'Warner',
 'KONAMI':'Konami','CD PROJEKT RED':'CD Projekt Red'}
# Ampliação decidida pelo grupo (Sprint 3): três publicadoras fora da lista do VideoGamesCritic
PUB_EXTRA={'KOEI TECMO GAMES CO., LTD.':'Koei Tecmo','Paradox Interactive':'Paradox','Paradox Arc':'Paradox','Larian Studios':'Larian'}
g['pubs']=g.game_publishers.apply(lambda L: sorted({PUB[x] for x in (L if L is not None else []) if x in PUB}))
g['C_pub']=g.pubs.str.len()>0
g['pubs_extra']=g.game_publishers.apply(lambda L: sorted({PUB_EXTRA[x] for x in (L if L is not None else []) if x in PUB_EXTRA}))
g['C_ext']=g.pubs_extra.str.len()>0
g['grupos']=(g.pubs+g.pubs_extra).apply(lambda L: sorted(set(L)))
g['AAA']=g.C_pub|g.C_ext   # CRITÉRIO ADOTADO (C4): C1 + Koei Tecmo, Paradox, Larian
tagset=t.set_index('game_id').tag_names.apply(lambda L:set(L) if L is not None else set())
g['tag_indie']=g.game_id.map(tagset).apply(lambda s: isinstance(s,set) and 'Indie' in s)
g['gen_indie']=g.game_genres.apply(lambda L: L is not None and 'Indie' in L)
tot=r.groupby('game_id').agg(n=('n','sum'),pos=('pos','sum'))
lang=r.pivot_table(index='game_id',columns='language',values='n',aggfunc='sum').fillna(0)
g=g.join(tot,on='game_id').join(lang[['english','brazilian','schinese']],on='game_id')
for c in ['n','pos','english','brazilian','schinese']: g[c]=g[c].fillna(0)
crit={
 'C1 Publicadoras (17 da VGC)': g.C_pub,
 'C1b Publicadoras sem tag Indie (regra VGC)': g.C_pub & ~g.tag_indie,
 'C2a Preço >= US$ 39,99': g.game_price>=39.99,
 'C2b Preço >= US$ 49,99': g.game_price>=49.99,
 'C2c Preço >= US$ 59,99': g.game_price>=59.99,
 'C3a Publicadoras E preço >= 39,99': g.C_pub & (g.game_price>=39.99),
 'C3b Publicadoras sem Indie E preço >= 39,99': g.C_pub & ~g.tag_indie & (g.game_price>=39.99),
 'C4 ADOTADO: C1 + Koei Tecmo, Paradox, Larian': g.AAA,
}
rows=[]; T=g.n.sum()
for k,m in crit.items():
    s=g[m]
    rows.append({'criterio':k,'jogos':int(m.sum()),'jogos_c_review':int((s.n>0).sum()),'reviews':int(s.n.sum()),'%_base':round(100*s.n.sum()/T,2),
     '%_pos':round(100*s.pos.sum()/max(s.n.sum(),1),1),'en':int(s.english.sum()),'pt_br':int(s.brazilian.sum()),'zh':int(s.schinese.sum())})
res=pd.DataFrame(rows); pd.set_option('display.width',250); print(res.to_string(index=False))
print('base total reviews',T, 'pos', round(100*g.pos.sum()/T,1),'(reviews de game_id sem cadastro ficam fora:', r.n.sum()-T,')')
print('\nprice null', g.game_price.isna().sum(), 'free', g.game_is_free.sum())
# sanity
print('\nTop 15 C1 por reviews:'); print(g[g.C_pub].nlargest(15,'n')[['game_name','pubs','game_price','tag_indie','n']].to_string(index=False))
print('\nC1 com tag Indie (top 10):'); print(g[g.C_pub&g.tag_indie].nlargest(10,'n')[['game_name','pubs','game_price','n']].to_string(index=False))
print('\nPreço>=59.99 sem publicadora (top 15):'); print(g[(g.game_price>=59.99)&~g.C_pub].nlargest(15,'n')[['game_name','game_publishers','game_price','n']].to_string(index=False))
print('\nC1 preço<39.99 (top 10):'); print(g[g.C_pub&(g.game_price<39.99)].nlargest(10,'n')[['game_name','pubs','game_price','game_is_free','n']].to_string(index=False))
print('\nPor publicadora (C1):'); e=g[g.C_pub].explode('pubs'); print(e.groupby('pubs').agg(jogos=('game_id','size'),reviews=('n','sum')).sort_values('reviews',ascending=False).to_string())
res.to_csv(D+'criterios_aaa.csv',index=False)
# lista final de jogos AAA (critério C4), lida por 05_base_final.py
g[g.AAA][['game_id','game_name','grupos','game_price','game_is_free','tag_indie','n','pos','english','brazilian']].assign(origem=lambda d: d.grupos.apply(lambda L: 'ampliacao' if set(L)<= {'Koei Tecmo','Paradox','Larian'} else 'VideoGamesCritic'), grupos=lambda d:d.grupos.str.join(';')).sort_values('n',ascending=False).to_csv(D+'jogos_aaa_selecionados.csv',index=False)
print('\nPor publicadora (C4):'); e=g[g.AAA].explode('grupos'); print(e.groupby('grupos').agg(jogos=('game_id','size'),reviews=('n','sum'),pos=('pos','sum')).assign(pct=lambda d:(100*d.pos/d.reviews).round(1)).sort_values('reviews',ascending=False).to_string())
g[g.C_pub][['game_id','game_name','pubs','game_price','game_is_free','tag_indie','gen_indie','n','pos','english','brazilian']].assign(pubs=lambda d:d.pubs.str.join(';')).sort_values('n',ascending=False).to_csv(D+'jogos_c1_publicadoras.csv',index=False)
