import requests,json,pathlib
id='0_iplk1pvk';out={}
for fmt in ['applehttp','m3u8','mpegdash','hdnetwork','hls','url','download']:
 u=f'https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/{id}/format/{fmt}/protocol/https'
 try:
  r=requests.get(u,timeout=15,headers={'User-Agent':'Mozilla/5.0'})
  out[fmt]={'code':r.status_code,'url':r.url[:300],'type':r.headers.get('Content-Type'),'text':r.text[:1200] if len(r.content)<300000 else 'large'}
 except Exception as e:out[fmt]={'error':str(e)}
 print(fmt,out[fmt]['code'] if 'code' in out[fmt] else out[fmt]['error'],out[fmt].get('type'),flush=True)
pathlib.Path('tmp_portsmouth_audit/quality_formats.json').write_text(json.dumps(out,indent=2))
