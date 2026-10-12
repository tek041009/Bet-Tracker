import requests,json,re,pathlib
O=pathlib.Path('tmp_portsmouth_audit');O.mkdir(exist_ok=True)
base='https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/{}/format/applehttp/protocol/https'
IDs={'WEST_HAM_EXTENDED':'0_iplk1pvk','WEST_HAM_GOALS':'0_4nzutk25'}
rpt={}
for name,id in IDs.items():
 try:
  r=requests.get(base.format(id),timeout=20,headers={'User-Agent':'Mozilla/5.0'})
  lines=r.text.splitlines()
  variants=[]
  for i,line in enumerate(lines):
   if '#EXT-X-STREAM-INF' in line:
    nxt=lines[i+1] if i+1<len(lines) else ''
    variants.append({'descriptor':line,'uri':nxt[:170]})
  rpt[name]={'http':r.status_code,'ct':r.headers.get('Content-Type'),'variants':variants}
  print(name,'variants',len(variants),flush=True)
  for v in variants:print(v['descriptor'],flush=True)
 except Exception as e:rpt[name]={'error':str(e)}
(O/'SOURCE_QUALITY_AUDIT.json').write_text(json.dumps(rpt,indent=2))
