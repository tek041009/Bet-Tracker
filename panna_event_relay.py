import duckdb,os,json,subprocess,pathlib,hashlib
group=os.environ['PANNA_GROUP']
groups={
 'english_uefa':'EPL Championship UCL UEL Conference_League FA_Cup League_Cup UEFA_Super_Cup'.split(),
 'european_leagues':'La_Liga Bundesliga Serie_A Ligue_1'.split(),
 'internationals':'AFCON AFCON_Qualifiers AFC_WC_Qualifiers CAF_WC_Qualifiers CONCACAF_Gold_Cup CONMEBOL_WC_Qualifiers Club_World_Cup Concacaf_Nations_League Copa_America FIFA_Intercontinental_Cup Intl_Friendlies UEFA_Euros UEFA_Nations_League UEFA_WC_Qualifiers World_Cup'.split()
}
clubs=groups['english_uefa']+groups['european_leagues'];intl=groups['internationals']
assert group in groups
folder=pathlib.Path('filtered_event_layers');folder.mkdir(exist_ok=True)
src=pathlib.Path('one_source.parquet')
base='https://github.com/peteowen1/pannadata/releases/download/opta-latest'
def download(name,path):
 subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','4','--retry-delay','2','--connect-timeout','20','--max-time','900','--output',str(path),base+'/'+name],check=True)
 assert path.stat().st_size>10000
download('opta_fixtures.parquet',src)
db=duckdb.connect();db.execute('SET threads=2');db.execute("SET memory_limit='6GB'")
db.execute("""CREATE TEMP TABLE wanted AS SELECT DISTINCT match_id FROM read_parquet(?) WHERE match_status='Played' AND ((competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')) OR (competition IN (SELECT UNNEST(?)) AND substr(match_date,1,10)>='2024-06-14' AND substr(match_date,1,10)<='2026-11-11'))""",[str(src),clubs,intl])
src.unlink()
report={'group':group,'source':'peteowen1/pannadata opta-latest','scope_matches':db.execute('SELECT count(*) FROM wanted').fetchone()[0],'files':{}}
for comp in groups[group]:
 name=f'events_{comp}.parquet'
 download(name,src)
 sha=hashlib.sha256(src.read_bytes()).hexdigest()
 columns=[c[0] for c in db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(src)]).fetchall()]
 assert 'match_id' in columns,(name,columns)
 output=folder/name
 db.execute(f"COPY (SELECT e.* FROM read_parquet('{src}') e JOIN wanted w USING(match_id)) TO '{output}' (FORMAT parquet, COMPRESSION zstd)")
 n,m=db.execute('SELECT count(*),count(distinct match_id) FROM read_parquet(?)',[str(output)]).fetchone()
 report['files'][name]={'source_sha256':sha,'source_size_bytes':src.stat().st_size,'filtered_size_bytes':output.stat().st_size,'rows':n,'matches':m,'columns':columns}
 print(group,name,'rows',n,'matches',m,'filtered MB',round(output.stat().st_size/1e6,2),flush=True)
 src.unlink()
(folder/'PROVENANCE.json').write_text(json.dumps(report,indent=2))
