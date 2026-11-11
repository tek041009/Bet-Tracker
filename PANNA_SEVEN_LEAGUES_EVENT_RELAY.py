#!/usr/bin/env python3
"""Recover ORIGINAL Opta event rows for seven additional relevant Panna leagues.
Keep original columns, selected fixture boundaries, upstream SHA256, and absence QA.
Does not treat absent events as zero and never changes any master SQLite.
"""
import os, pathlib, json, hashlib, subprocess, urllib.request, time, datetime
import duckdb

GROUPS = {
    'netherlands_portugal': ['Eredivisie','Primeira_Liga'],
    'turkey_scotland': ['Super_Lig','Scottish_Premiership'],
    'english_lower': ['League_One','League_Two'],
    'wsl': ['WSL'],
}
GROUP=os.environ['PANNA_SEVEN_GROUP']; assert GROUP in GROUPS,GROUP
RELEASE='https://github.com/peteowen1/pannadata/releases/download/opta-latest'
root=pathlib.Path('panna_seven_event_sources');root.mkdir(exist_ok=True)
source=pathlib.Path('panna_upstream_source.parquet')
req=urllib.request.Request('https://api.github.com/repos/peteowen1/pannadata/releases/tags/opta-latest',headers={'User-Agent':'Panna-Seven-Leagues-20261111/1.0'})
with urllib.request.urlopen(req,timeout=60) as r: upstream=json.load(r)
release_assets={a['name']:a for a in upstream['assets']}

def download(name):
    assert name in release_assets,name
    subprocess.run(['curl','--fail','--location','--silent','--show-error','--retry','4','--retry-all-errors','--retry-delay','2','--connect-timeout','25','--max-time','1200','--output',str(source),RELEASE+'/'+name],check=True)
    size=source.stat().st_size
    with source.open('rb') as handle: digest=hashlib.file_digest(handle,'sha256').hexdigest()
    m=release_assets[name]
    assert size==m['size'] and m['digest']==f'sha256:{digest}',(name,size,digest)
    return {'source_name':name,'source_size':size,'source_sha256':digest,'source_updated_at':m['updated_at'],'release_asset_id':m['id']}

db=duckdb.connect(':memory:');db.execute('SET threads=2');db.execute("SET memory_limit='5GB'")
fixture=download('opta_fixtures.parquet')
competitions=GROUPS[GROUP]
db.execute("CREATE TEMP TABLE wanted AS SELECT match_id,competition,season,match_date FROM read_parquet(?) WHERE match_status='Played' AND competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')",[str(source),competitions])
selected=db.execute('SELECT competition,count(*),min(match_date),max(match_date) FROM wanted GROUP BY competition').fetchall()
fixture_rows=db.execute('SELECT count(*) FROM wanted').fetchone()[0]
assert fixture_rows>0
source.unlink()
report={'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'group':GROUP,'scope_competitions':competitions,'club_seasons':['2025-2026','2026-2027'],'fixture_source':fixture,'selected_fixtures':fixture_rows,'fixture_summary':selected,'event_sources':{}}
for comp in competitions:
    name=f'events_{comp}.parquet'
    meta=download(name)
    cols=[x[0] for x in db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(source)]).fetchall()]
    assert all(k in cols for k in ['match_id','event_id','player_id','team_id','x','y','competition','season']), (name,cols)
    expected=db.execute('SELECT count(*) FROM wanted WHERE competition=?',[comp]).fetchone()[0]
    target=root/name
    db.execute(f"COPY (SELECT e.* FROM read_parquet('{source}') e JOIN (SELECT DISTINCT match_id FROM wanted WHERE competition='{comp}') w USING(match_id)) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    rows,match_count=db.execute('SELECT count(*),count(distinct match_id) FROM read_parquet(?)',[str(target)]).fetchone()
    dupes=db.execute('SELECT count(*) FROM (SELECT match_id,event_id,count(*) n FROM read_parquet(?) GROUP BY match_id,event_id HAVING n>1)',[str(target)]).fetchone()[0]
    with target.open('rb') as handle: filtered_sha=hashlib.file_digest(handle,'sha256').hexdigest()
    report['event_sources'][name]={**meta,'original_columns':cols,'selected_rows':rows,'selected_unique_matches':match_count,'expected_fixture_count':expected,'missing_event_match_count':expected-match_count,'duplicate_match_event_id_keys':dupes,'filtered_file':str(target),'filtered_size_bytes':target.stat().st_size,'filtered_sha256':filtered_sha}
    print('COMP',comp,'fixtures',expected,'events',rows,'with_events',match_count,'missing',expected-match_count,'duplicate_event_keys',dupes,'filtered_bytes',target.stat().st_size,flush=True)
    assert rows>0 and 0<=match_count<=expected and dupes==0
    source.unlink()
(root/'PROVENANCE.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
print('SOURCE_GROUP_COMPLETE',GROUP,fixture_rows,flush=True)
