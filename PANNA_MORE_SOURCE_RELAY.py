#!/usr/bin/env python3
"""Download exact Panna upstream assets to isolated GH Actions runner; filter with auditable rules.

Outputs Parquet with original columns preserved; never silently use an inferred join key.
CLI group from PANNA_EXTRA_GROUP. Anything with unsafely unknown scope is flagged rather than represented as loaded.
"""
import os,sys,json,hashlib,subprocess,pathlib,datetime
from urllib.request import urlopen, Request
import duckdb

GROUPS={
'advanced':['opta-latest:opta_match_stats.parquet','opta-latest:opta_skills.parquet'],
'profiles':['opta-latest:opta_players.parquet','opta-latest:squads.parquet','opta-latest:event_less_match_ids.parquet','opta-latest:opta-manifest.parquet','opta-latest:league_strength.parquet'],
'weekly_epr':['opta-latest:opta_epr_weekly.parquet'],
'weekly_psr':['opta-latest:opta_psr_weekly.parquet'],
'career_asof':['ratings-data:career_panna_asof.parquet'],
'ratings_other':['ratings-data:seasonal_xrapm.parquet','ratings-data:seasonal_spm.parquet','ratings-data:seasonal_rapm_raw.parquet','ratings-data:pooled_rapm_raw.parquet','ratings-data:career_panna.parquet','ratings-data:career_spm.parquet','ratings-data:player_metadata.parquet'],
'models_big':['models:epv_model.rds','models:xg_model.rds'],
'models_other':['models:xgot_model.rds','models:xgot_model_v3.rds','models:xg_model_v5.rds','models:wp_model.rds','models:xpass_model.rds']
}
CLUBS='EPL La_Liga Bundesliga Serie_A Ligue_1 Championship UCL UEL Conference_League FA_Cup League_Cup UEFA_Super_Cup'.split()
INTL='AFCON AFCON_Qualifiers AFC_WC_Qualifiers CAF_WC_Qualifiers CONCACAF_Gold_Cup CONMEBOL_WC_Qualifiers Club_World_Cup Concacaf_Nations_League Copa_America FIFA_Intercontinental_Cup Intl_Friendlies UEFA_Euros UEFA_Nations_League UEFA_WC_Qualifiers World_Cup'.split()
GROUP=os.environ.get('PANNA_EXTRA_GROUP','')
if GROUP not in GROUPS: raise ValueError('Unsupported group '+str(GROUP))
OUT=pathlib.Path('panna_extra_data');OUT.mkdir(exist_ok=True)
SRC=pathlib.Path('one_source.bin')
BASE='https://github.com/peteowen1/pannadata/releases/download'

def digest_file(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def dl(release,filename):
 url=f'{BASE}/{release}/{filename}'
 subprocess.run(['curl','--fail','--silent','--show-error','--location','--retry','5','--retry-all-errors','--retry-delay','2','--connect-timeout','30','--max-time','1800','--output',str(SRC),url],check=True)
 if SRC.stat().st_size==0:raise RuntimeError(f'Empty asset {filename}')
 return str(SRC)

def get_manifest(release):
 url=f'https://api.github.com/repos/peteowen1/pannadata/releases/tags/{release}'
 with urlopen(Request(url,headers={'User-Agent':'PannaScopeQA/1.0'}),timeout=60) as r:meta=json.load(r)
 return {x['name']:{'size':x['size'],'digest':x.get('digest'),'updated_at':x.get('updated_at'),'asset_id':x['id']} for x in meta['assets']}

report={'group':GROUP,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_repo':'peteowen1/pannadata','scope':'Original 27-comp selection, 2025-2027 domestic seasons, international 2024-06-14..2026-11-11',
 'rules':{'exact_match_id':'join original match_id to source fixture wanted','domestic_competition_season':'competition/league and season constrained to 2025-2027','profile_or_rating':'unfiltered original parquet, no evidence-safe selector','unknown_large':'not imported; schema and full-source SHA recorded'},'files':{}}
needed={x.split(':')[0] for x in GROUPS[GROUP]}
needed.add('opta-latest')
manifest={r:get_manifest(r) for r in sorted(needed)}
db=duckdb.connect(':memory:');db.execute('SET threads=2');db.execute("SET memory_limit='5GB'")
if GROUP in ('advanced','profiles','weekly_epr','weekly_psr'):
 dl('opta-latest','opta_fixtures.parquet')
 fixtures_digest=digest_file(SRC)
 expected=manifest['opta-latest']['opta_fixtures.parquet']
 assert SRC.stat().st_size==expected['size']
 assert 'sha256:'+fixtures_digest==expected['digest'], 'Fixture sha mismatch'
 db.execute('''CREATE TABLE wanted AS SELECT DISTINCT match_id FROM read_parquet(?) WHERE match_status='Played' AND ((competition IN (SELECT UNNEST(?)) AND season IN ('2025-2026','2026-2027')) OR (competition IN (SELECT UNNEST(?)) AND substr(match_date,1,10) BETWEEN '2024-06-14' AND '2026-11-11'))''',[str(SRC),CLUBS,INTL])
 report['source_fixture_sha256']=fixtures_digest
 report['source_fixture_scope_matches']=db.execute('SELECT count(*) FROM wanted').fetchone()[0]
 SRC.unlink()
for release_name in GROUPS[GROUP]:
 release,name=release_name.split(':',1)
 meta=manifest[release][name]
 dl(release,name)
 sha=digest_file(SRC)
 assert meta['digest']=='sha256:'+sha,(name,'Source official sha mismatch',sha,meta['digest'])
 assert SRC.stat().st_size==meta['size'],(name,'Source official file size mismatch')
 info={'release':release,'source_sha256':sha,'source_size':SRC.stat().st_size,'source_modified':meta['updated_at'],'source_asset_id':meta['asset_id'],'source_url':f'{BASE}/{release}/{name}'}
 target=OUT/name
 if name.endswith('.rds'):
  target.write_bytes(SRC.read_bytes());info.update({'filter':'native trained-model binary, byte-identical','stored_sha256':digest_file(target),'stored_bytes':target.stat().st_size})
 else:
  cols=[x[0] for x in db.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(SRC)]).fetchall()]
  orig_rows=db.execute('SELECT count(*) FROM read_parquet(?)',[str(SRC)]).fetchone()[0]
  info.update({'source_rows':orig_rows,'source_columns':cols})
  # Restrict only if source directly supports an evidence-safe key.
  if 'match_id' in cols and GROUP not in ('ratings_other','career_asof'):
   q="SELECT s.* FROM read_parquet('one_source.bin') s JOIN wanted w USING(match_id)"
   info['filter']='match_id join to wanted match IDs'
  elif GROUP in ('advanced','weekly_epr','weekly_psr'):
   c=next((x for x in ['competition','league'] if x in cols),None)
   if c and 'season' in cols:
    q=f"SELECT * FROM read_parquet('one_source.bin') WHERE {c} IN ({','.join(repr(x) for x in CLUBS+INTL)}) AND (season IN ('2025-2026','2026-2027') OR season LIKE '%2026%')"
    info['filter']='competition/league + season source keys'
   elif 'season' in cols:
    q="SELECT * FROM read_parquet('one_source.bin') WHERE season IN ('2025-2026','2026-2027') OR season LIKE '%2026%'"
    info['filter']='season only, coverage needing later joins'
   else:
    q=None;info['filter']='UNSAFE_SCOPE_DEFERRED: original not imported';info['reason']='No match_id or known season/league key'
  else:
   q="SELECT * FROM read_parquet('one_source.bin')";info['filter']='all original source rows retained, no safe temporal filter'
  if q:
   db.execute(f"COPY ({q}) TO '{target.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
   info.update({'stored_rows':db.execute('SELECT count(*) FROM read_parquet(?)',[str(target)]).fetchone()[0],
     'stored_bytes':target.stat().st_size,'stored_sha256':digest_file(target)})
   if 'match_id' in cols:
    info['stored_match_ids']=db.execute('SELECT count(distinct match_id) FROM read_parquet(?)',[str(target)]).fetchone()[0]
 SRC.unlink()
 report['files'][name]=info
 print('ASSET',GROUP,name,'source MB',round(info['source_size']/1e6,1),'rows',info.get('source_rows'), 'filtered',info.get('stored_rows'), 'bytes',info.get('stored_bytes',0),'policy',info['filter'],flush=True)
(OUT/'PROVENANCE.json').write_text(json.dumps(report,indent=2))
