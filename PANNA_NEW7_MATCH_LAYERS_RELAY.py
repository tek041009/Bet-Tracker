#!/usr/bin/env python3
"""Verified upstream Panna supplemental match layers for seven added competitions.
Copies original field names and original Panna rows; source SHA and matched fixture IDs audited.
"""
import os,pathlib,hashlib,json,subprocess,urllib.request,datetime
import duckdb
ASSETS={
 'shot_summary':'opta_shots.parquet',
 'shot_events':'opta_shot_events.parquet',
 'lineups':'opta_lineups.parquet',
 'timed_events':'opta_events.parquet',
 'xmetrics_bymatch':'opta_xmetrics_bymatch.parquet',
 'advanced_match_stats':'opta_match_stats.parquet',
}
comp=['Eredivisie','Primeira_Liga','Super_Lig','Scottish_Premiership','League_One','League_Two','WSL']
job=os.environ['PANNA_NEW7_MATCH_LAYER'];assert job in ASSETS,job
name=ASSETS[job]
folder=pathlib.Path('panna_new7_match_layers');folder.mkdir(exist_ok=True)
source=pathlib.Path('source_original.parquet')
base='https://github.com/peteowen1/pannadata/releases/download/opta-latest/'
url='https://api.github.com/repos/peteowen1/pannadata/releases/tags/opta-latest'
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Panna-New7-Layer-Audit'}),timeout=60) as r:rel=json.load(r)
assets={a['name']:a for a in rel['assets']}

def download(filename):
 subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','25','--max-time','1600','--output',str(source),base+filename],check=True)
 with source.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 a=assets[filename]
 assert source.stat().st_size==a['size'] and a['digest']=='sha256:'+sha,(filename,'source bytes differ from release')
 return {'filename':filename,'sha256':sha,'bytes':source.stat().st_size,'updated_at':a['updated_at'],'id':a['id']}
DB=duckdb.connect(':memory:');DB.execute('SET threads=2');DB.execute("SET memory_limit='5GB'")
fixture=download('opta_fixtures.parquet')
DB.execute("CREATE TABLE wanted AS SELECT DISTINCT match_id,competition,season FROM read_parquet(?) WHERE match_status='Played' AND competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')",[str(source),comp])
nwanted=DB.execute('SELECT count(*) FROM wanted').fetchone()[0]
assert nwanted==3139,('fixture snapshot changed',nwanted)
source.unlink()
asset=download(name)
cols=[r[0] for r in DB.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(source)]).fetchall()]
assert 'match_id' in cols,(name,cols)
orig_rows=DB.execute('SELECT count(*) FROM read_parquet(?)',[str(source)]).fetchone()[0]
target=folder/name
DB.execute(f"COPY (SELECT o.* FROM read_parquet('{source}') o JOIN (SELECT DISTINCT match_id FROM wanted) w USING(match_id)) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
selected_rows,matched=DB.execute('SELECT count(*),count(distinct match_id) FROM read_parquet(?)',[str(target)]).fetchone()
with target.open('rb') as f:filtered=hashlib.file_digest(f,'sha256').hexdigest()
assert selected_rows>0 and matched<=nwanted
coverage=DB.execute('''SELECT w.competition,count(distinct w.match_id),count(distinct o.match_id),count(o.match_id) FROM wanted w LEFT JOIN read_parquet(?) o USING(match_id) GROUP BY w.competition ORDER BY w.competition''',[str(target)]).fetchall()
report={'group':job,'as_of':'2026-11-11','source_asset':asset,'fixture_asset':fixture,'scope_leagues':comp,'club_seasons':['2025-2026','2026-2027'],'source_rows':orig_rows,'source_columns':cols,'selected_rows':selected_rows,'matched_fixture_ids':matched,'expected_fixture_ids':nwanted,'coverage_by_competition':coverage,'filtered_filename':target.name,'filtered_file_bytes':target.stat().st_size,'filtered_file_sha256':filtered,'source_note':'Original columns. Missing matches must be INSUFFICIENT, never zero. Original 27 competition data not altered.'}
(folder/'PROVENANCE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print('DONE',job,'original',orig_rows,'selected',selected_rows,'matched',matched,'filtered MB',target.stat().st_size/1e6,flush=True)
