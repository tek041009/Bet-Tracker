#!/usr/bin/env python3
"""Verify and extract dated Panna skills, EPR and PSR for the additional seven-league player universe.
Never interpret a weekly snapshot as a match; source rows and columns unchanged.
"""
import os,pathlib,subprocess,hashlib,urllib.request,json,datetime
import duckdb
GROUP=os.environ['PANNA_NEW7_DYNAMIC_GROUP']
WINDOWS={'2025h2':('2025-07-01','2025-12-31'),'2026h1':('2026-01-01','2026-06-30'),'2026h2':('2026-07-01','2026-11-11')}
if GROUP=='skills': file='opta_skills.parquet'; window=None
else:
 kind,part=GROUP.split('_');assert kind in ['epr','psr'] and part in WINDOWS
 file={'epr':'opta_epr_weekly.parquet','psr':'opta_psr_weekly.parquet'}[kind];window=WINDOWS[part]
ALL=['Eredivisie','Primeira_Liga','Super_Lig','Scottish_Premiership','League_One','League_Two','WSL']
OUT=pathlib.Path('panna_new7_dynamics');OUT.mkdir(exist_ok=True);SRC=pathlib.Path('source.parquet')
with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/peteowen1/pannadata/releases/tags/opta-latest',headers={'User-Agent':'Panna-New7-Dynamics/1.0'}),timeout=60) as r:release=json.load(r)
assets={a['name']:a for a in release['assets']}
BASE='https://github.com/peteowen1/pannadata/releases/download/opta-latest/'
def download(name):
 subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','25','--max-time','1600','--output',str(SRC),BASE+name],check=True)
 with SRC.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 a=assets[name];assert SRC.stat().st_size==a['size'] and a['digest']=='sha256:'+sha
 return {'asset':name,'sha256':sha,'source_bytes':a['size'],'source_modified':a['updated_at']}
DB=duckdb.connect(':memory:');DB.execute('SET threads=2');DB.execute("SET memory_limit='5GB'")
fixture=download('opta_fixtures.parquet')
DB.execute("CREATE TEMP TABLE wanted AS SELECT DISTINCT match_id FROM read_parquet(?) WHERE match_status='Played' AND competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')",[str(SRC),ALL]);assert DB.execute('select count(*) from wanted').fetchone()[0]==3139
SRC.unlink()
lineups=download('opta_lineups.parquet')
DB.execute('CREATE TEMP TABLE wanted_players AS SELECT DISTINCT l.player_id FROM read_parquet(?) l JOIN wanted w USING(match_id) WHERE l.player_id IS NOT NULL',[str(SRC)])
player_count=DB.execute('select count(*) from wanted_players').fetchone()[0];assert 4000<player_count<10000,player_count
SRC.unlink()
source=download(file)
columns=[r[0] for r in DB.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(SRC)]).fetchall()];assert 'player_id' in columns
orig_rows=DB.execute('SELECT count(*) FROM read_parquet(?)',[str(SRC)]).fetchone()[0]
if GROUP=='skills':
 assert 'date' in columns and 'season_end_year' in columns
 cond="TRY_CAST(s.date AS DATE)<='2026-11-11' AND TRY_CAST(s.season_end_year AS INTEGER)>=2024"
else:
 assert 'snapshot_date' in columns
 cond=f"TRY_CAST(s.snapshot_date AS DATE) BETWEEN '{window[0]}' AND '{window[1]}'"
TARGET=OUT/(GROUP+'.parquet')
DB.execute(f"COPY (SELECT s.* FROM read_parquet('{SRC}') s JOIN wanted_players w USING(player_id) WHERE {cond}) TO '{TARGET}' (FORMAT PARQUET, COMPRESSION ZSTD)")
selected,players=DB.execute('SELECT count(*),count(distinct player_id) FROM read_parquet(?)',[str(TARGET)]).fetchone();assert selected>0
with TARGET.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
report={'job':GROUP,'source':source,'selected_7_competitions':ALL,'source_fixture':fixture,'source_lineups':lineups,'source_rows':orig_rows,'original_columns':columns,'filter':cond,'new_seven_distinct_players':player_count,'selected_rows':selected,'selected_players':players,'selected_file':TARGET.name,'filtered_bytes':TARGET.stat().st_size,'filtered_sha256':sha,'window':window,'as_of':'2026-11-11','not_match_data':'These are dated ratings and profile summaries; do not count snapshots as matches.'}
(OUT/'PROVENANCE.json').write_text(json.dumps(report,indent=2)+'\n')
print('DONE',GROUP,'source',orig_rows,'selected',selected,'players',players,'bytes',TARGET.stat().st_size,flush=True)
