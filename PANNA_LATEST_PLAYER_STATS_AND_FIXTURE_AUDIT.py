#!/usr/bin/env python3
"""Fetch latest published Opta core player stats and fixture catalogue for source-vs-local match QA.
Does not alter existing SQLite; creates exact-column source Parquet snapshots and match-ID manifest.
"""
import pathlib,datetime,hashlib,json,subprocess
from urllib.request import urlopen,Request
import duckdb
OUT=pathlib.Path('panna_latest_core');OUT.mkdir(exist_ok=True)
SRC=pathlib.Path('source.parquet')
BASE='https://github.com/peteowen1/pannadata/releases/download/opta-latest'
PRIMARY='EPL La_Liga Bundesliga Serie_A Ligue_1 Championship UCL UEL Conference_League FA_Cup League_Cup UEFA_Super_Cup'.split()
INTL='AFCON AFCON_Qualifiers AFC_WC_Qualifiers CAF_WC_Qualifiers CONCACAF_Gold_Cup CONMEBOL_WC_Qualifiers Club_World_Cup Concacaf_Nations_League Copa_America FIFA_Intercontinental_Cup Intl_Friendlies UEFA_Euros UEFA_Nations_League UEFA_WC_Qualifiers World_Cup'.split()
ADDITIONAL='Eredivisie Primeira_Liga Super_Lig Scottish_Premiership League_One League_Two WSL'.split()
with urlopen(Request('https://api.github.com/repos/peteowen1/pannadata/releases/tags/opta-latest',headers={'User-Agent':'Panna-Core-Snapshot-Validation'}),timeout=60) as r:release=json.load(r)
meta={a['name']:a for a in release['assets']}
def load(name):
 subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','5','--retry-all-errors','--retry-delay','2','--connect-timeout','30','--max-time','1800','--output',str(SRC),BASE+'/'+name],check=True)
 h=hashlib.file_digest(SRC.open('rb'),'sha256').hexdigest()
 assert SRC.stat().st_size==meta[name]['size'] and h==meta[name]['digest'].removeprefix('sha256:')
 return {'source_bytes':SRC.stat().st_size,'source_sha256':h,'source_updated_at':meta[name]['updated_at']}
db=duckdb.connect(':memory:');db.execute('SET threads=2');db.execute("SET memory_limit='5GB'")
fix=load('opta_fixtures.parquet')
db.execute("CREATE TABLE wanted_primary AS SELECT * FROM read_parquet('source.parquet') WHERE match_status='Played' AND ((competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')) OR (competition IN (SELECT UNNEST(?)) AND substr(match_date,1,10) BETWEEN '2024-06-14' AND '2026-11-11'))",[PRIMARY,INTL])
db.execute("CREATE TABLE wanted_more AS SELECT * FROM read_parquet('source.parquet') WHERE match_status='Played' AND competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')",[ADDITIONAL])
# retain full schema fixture rows per available competition and both seasons.
db.execute("COPY (SELECT * FROM wanted_primary UNION ALL BY NAME SELECT * FROM wanted_more) TO 'panna_latest_core/selected_fixtures.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)")
fixture_rows=db.execute('SELECT competition,season,count(*),min(match_date),max(match_date) FROM (SELECT * FROM wanted_primary UNION ALL BY NAME SELECT * FROM wanted_more) GROUP BY competition,season ORDER BY competition,season').fetchall()
fixids=db.execute('SELECT DISTINCT match_id FROM (SELECT * FROM wanted_primary UNION ALL BY NAME SELECT * FROM wanted_more)').fetchall()
print('FIXTURES',len(fixids),'GROUPS',len(fixture_rows),flush=True)
SRC.unlink()
stats=load('opta_player_stats.parquet')
source_cols=[v[0] for v in db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(SRC)]).fetchall()]
assert 'match_id' in source_cols
info={}
for group in ['wanted_primary','wanted_more']:
 target=OUT/f'{group}_player_stats.parquet'
 q=f"SELECT s.* FROM read_parquet('source.parquet') s JOIN (SELECT DISTINCT match_id FROM {group}) w USING(match_id)"
 db.execute(f"COPY ({q}) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
 a=db.execute('SELECT COUNT(*),COUNT(DISTINCT match_id) FROM read_parquet(?)',[str(target)]).fetchone()
 info[group]={'player_rows':a[0],'match_ids':a[1],'filtered_bytes':target.stat().st_size,'filtered_sha256':hashlib.file_digest(target.open('rb'),'sha256').hexdigest()}
 print('PLAYER_STATS',group,info[group],flush=True)
SRC.unlink()
report={'as_of':'2026-11-11','source':'peteowen1/pannadata opta-latest','verified_source_fixtures':fix,
 'verified_source_player_stats':stats,'source_columns':source_cols,'fixture_counts':fixture_rows,
 'selection':{'primary27':PRIMARY+INTL,'additional7':ADDITIONAL,'club_seasons':['2025-2026','2026-2027'],'international_after':'2024-06-14','before':'2026-11-11'},
 'filtered':info,'local_master_comparison':'REQUIRES local V5/V7 exact match-ID join; do not infer matches complete from raw source count'}
(OUT/'PROVENANCE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print('DONE',flush=True)
