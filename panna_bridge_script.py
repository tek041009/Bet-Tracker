import duckdb, os, json, pathlib, subprocess, hashlib, time
base='https://github.com/peteowen1/pannadata/releases/download/opta-latest'
src=pathlib.Path('source');out=pathlib.Path('filtered');src.mkdir(exist_ok=True);out.mkdir(exist_ok=True)
assets=['opta_shot_events.parquet','opta_lineups.parquet','opta_events.parquet','opta_xmetrics_bymatch.parquet','opta_xmetrics.parquet','opta_match_xg.parquet']
clubs='EPL La_Liga Bundesliga Serie_A Ligue_1 Championship UCL UEL Conference_League FA_Cup League_Cup UEFA_Super_Cup'.split()
intl='AFCON AFCON_Qualifiers AFC_WC_Qualifiers CAF_WC_Qualifiers CONCACAF_Gold_Cup CONMEBOL_WC_Qualifiers Club_World_Cup Concacaf_Nations_League Copa_America FIFA_Intercontinental_Cup Intl_Friendlies UEFA_Euros UEFA_Nations_League UEFA_WC_Qualifiers World_Cup'.split()
for name in ['opta_fixtures.parquet']+assets:
 dest=src/name
 subprocess.run(['curl','--fail','--location','--retry','4','--retry-delay','2','--connect-timeout','20','--max-time','900','--output',str(dest),base+'/'+name],check=True)
 if dest.stat().st_size<10000:raise RuntimeError('small file '+name)
 print('downloaded',name,dest.stat().st_size,flush=True)
db=duckdb.connect(':memory:');db.execute('SET threads=2');db.execute('SET memory_limit=5GB')
db.execute('''CREATE TABLE wanted AS SELECT DISTINCT match_id FROM read_parquet(?) WHERE match_status='Played' AND ((competition in (SELECT UNNEST(?)) and season IN ('2025-2026','2026-2027')) OR (competition in (SELECT UNNEST(?)) and substr(match_date,1,10) >= '2024-06-14' and substr(match_date,1,10)<='2026-11-11'))''',[str(src/'opta_fixtures.parquet'),clubs,intl])
print('scoped',db.execute('SELECT COUNT(*) FROM wanted').fetchone(),flush=True)
report={'scoped_matches':db.execute('select count(*) from wanted').fetchone()[0],'asset_scope':'27 chosen competitions, two domestic seasons, international >= 2024-06-14','assets':{}}
for name in assets:
 p=src/name;sha=hashlib.sha256(p.read_bytes()).hexdigest()
 describe=db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(p)]).fetchall();cols=[c[0] for c in describe]
 if 'match_id' in cols:
  select=f"SELECT s.* FROM read_parquet('{p}') s JOIN wanted w USING(match_id)"
 elif 'league' in cols and 'season' in cols:
  select=f"SELECT * FROM read_parquet('{p}') WHERE league IN ({','.join(repr(x) for x in clubs)}) AND season IN ('2025-2026','2026-2027')"
 elif 'competition' in cols and 'season' in cols:
  select=f"SELECT * FROM read_parquet('{p}') WHERE competition IN ({','.join(repr(x) for x in clubs)}) AND season IN ('2025-2026','2026-2027')"
 else:
  print('UNSCOPED_SCHEMA',name,cols,flush=True);continue
 target=out/name
 db.execute(f"COPY ({select}) TO '{target}' (FORMAT parquet, COMPRESSION zstd)")
 count=db.execute(f'SELECT count(*) FROM read_parquet(?)',[str(target)]).fetchone()[0]
 games=db.execute(f'SELECT count(distinct match_id) FROM read_parquet(?)',[str(target)]).fetchone()[0] if 'match_id' in cols else None
 report['assets'][name]={'source_size':p.stat().st_size,'sha256':sha,'filtered_size':target.stat().st_size,'rows':count,'games':games,'columns':cols}
 print('FILTERED',name,'rows',count,'games',games,'outMB',round(target.stat().st_size/1e6,1),flush=True)
(out/'PROVENANCE.json').write_text(json.dumps(report,indent=2))
