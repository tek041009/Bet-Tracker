#!/usr/bin/env python3
"""Recover Panna weekly rating histories and skills for exact current fixture player universe.
Snapshot dates are filtered without inferring match-level evidence from weekly rows.
"""
import os,json,pathlib,subprocess,hashlib,datetime
from urllib.request import urlopen,Request
import duckdb

job=os.environ['PANNA_WEEKLY_GROUP']
windows={'2025h2':('2025-07-01','2025-12-31'),
 '2026h1':('2026-01-01','2026-06-30'),
 '2026h2':('2026-07-01','2026-11-11')}
if job!='skills' and not (job.startswith('epr_') or job.startswith('psr_')):raise ValueError(job)
kind=job.split('_')[0]
window=windows.get(job.split('_')[-1]);assert job=='skills' or window
assets={'skills':'opta_skills.parquet','epr':'opta_epr_weekly.parquet','psr':'opta_psr_weekly.parquet'}
asset=assets[kind];out=pathlib.Path('panna_weekly_recovered');out.mkdir(exist_ok=True)
src=pathlib.Path('source.parquet')
base='https://github.com/peteowen1/pannadata/releases/download/opta-latest'
def download(name):
 subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','5','--retry-all-errors','--retry-delay','2','--connect-timeout','30','--max-time','1800','--output',str(src),base+'/'+name],check=True)
 assert src.stat().st_size>10000,name
 return src

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
with urlopen(Request('https://api.github.com/repos/peteowen1/pannadata/releases/tags/opta-latest',headers={'User-Agent':'Panna-Safe-Scope/1.0'}),timeout=45) as r:release=json.load(r)
metas={a['name']:a for a in release['assets']}
def verified(name):
 download(name)
 meta=metas[name]
 assert src.stat().st_size==meta['size']
 d=sha(src);assert meta['digest']=='sha256:'+d,(name,'source digest mismatch')
 return {'bytes':src.stat().st_size,'sha256':d,'source_modified':meta['updated_at']}

DB=duckdb.connect(':memory:');DB.execute('SET threads=2');DB.execute("SET memory_limit='5GB'")
fixtures=verified('opta_fixtures.parquet')
clubs='EPL La_Liga Bundesliga Serie_A Ligue_1 Championship UCL UEL Conference_League FA_Cup League_Cup UEFA_Super_Cup'.split()
intl='AFCON AFCON_Qualifiers AFC_WC_Qualifiers CAF_WC_Qualifiers CONCACAF_Gold_Cup CONMEBOL_WC_Qualifiers Club_World_Cup Concacaf_Nations_League Copa_America FIFA_Intercontinental_Cup Intl_Friendlies UEFA_Euros UEFA_Nations_League UEFA_Super_Cup UEFA_WC_Qualifiers World_Cup'.split()
DB.execute("CREATE TEMP TABLE wanted_matches AS SELECT DISTINCT match_id FROM read_parquet('source.parquet') WHERE match_status='Played' AND ((competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')) OR (competition IN (SELECT UNNEST(?)) AND substr(match_date,1,10) BETWEEN '2024-06-14' AND '2026-11-11'))",[clubs,intl])
src.unlink()
lineups=verified('opta_lineups.parquet')
DB.execute("CREATE TEMP TABLE wanted_players AS SELECT DISTINCT l.player_id FROM read_parquet('source.parquet') l JOIN wanted_matches m USING(match_id) WHERE l.player_id IS NOT NULL AND length(l.player_id)>0")
players=DB.execute('SELECT count(*) FROM wanted_players').fetchone()[0]
assert 1000<=players<=100000,players
src.unlink()
source=verified(asset)
rows=DB.execute("SELECT count(*) FROM read_parquet('source.parquet')").fetchone()[0]
cols=[x[0] for x in DB.execute("DESCRIBE SELECT * FROM read_parquet('source.parquet')").fetchall()]
assert 'player_id' in cols
if kind=='skills':
 assert 'season_end_year' in cols and 'date' in cols
 where="TRY_CAST(s.season_end_year AS INTEGER) >= 2024 AND TRY_CAST(s.date AS DATE)<='2026-11-11'"
else:
 assert 'snapshot_date' in cols
 where=f"TRY_CAST(s.snapshot_date AS DATE) BETWEEN '{window[0]}' AND '{window[1]}'"
q=f"SELECT s.* FROM read_parquet('source.parquet') s JOIN wanted_players w USING(player_id) WHERE {where}"
target=out/(job+'.parquet')
DB.execute(f"COPY ({q}) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
count=DB.execute('SELECT count(*) FROM read_parquet(?)',[str(target)]).fetchone()[0]
assert count>0,('zero scoped rows',job)
sha_target=sha(target)
report={'job':job,'as_of':'2026-11-11','source_name':asset,'source':source,'source_rows':rows,
 'output_rows':count,'output_bytes':target.stat().st_size,'output_sha256':sha_target,'original_columns':cols,
 'filter':where,'player_join':'Opta original player_id matched to original Opta lineups for 27 competition scope','wanted_players':players,
 'wanted_matches':DB.execute('select count(*) from wanted_matches').fetchone()[0],
 'source_fixtures':fixtures,'source_lineups':lineups,'window':window,
 'note':'Original rows/columns preserved; these are dated snapshots, not match-level stats. Never treat multiple snapshots as independent matches or as current XI.'}
(out/'PROVENANCE.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'group':job,'source_rows':rows,'selected_rows':count,'selected_bytes':target.stat().st_size,'players':players,'filter':where},indent=2),flush=True)
