import requests,re,json,pathlib,html
out={}
urls=[
'https://std-pre-prod.whufc.com/en/matches/mens-team/west-ham-united-fc-v-portsmouth-fc-league-cup-20260808?tab=post-match',
'https://www.whufc.com/en/video',
'https://www.whufc.com/en/video/playlists/goals',
'https://www.whufc.com/en/video/playlists/highlights-0',
'https://www.whufc.com/en/video/0_vl8rtoz7'
]
for i,url in enumerate(urls):
 o={'url':url}
 try:
  r=requests.get(url,timeout=15,headers={'User-Agent':'Mozilla/5.0'});s=r.text
  o['http']=r.status_code;o['size']=len(s);o['kaltura_ids']=list(dict.fromkeys(re.findall(r'0_[a-z0-9]{8}',s)))[:100]
  for term in ('Goals | West Ham United 3-1 Portsmouth','Bowen | It’s a good way to start','Portsmouth','kaltura','partnerId','entryId','playManifest','VideoPlayer','brightcove'):
   matches=list(re.finditer(re.escape(term),s,re.I))
   o['term_'+term]={'n':len(matches),'snippets':[s[max(0,m.start()-450):m.end()+600] for m in matches[:3]]}
  o['media_links']=[s[max(0,m.start()-50):m.end()+150] for m in list(re.finditer(r'https?:[^\" \\\\]{3,200}(?:\\.m3u8|\\.mp4)',s,re.I))[:12]]
 except Exception as e:o['error']=str(e)
 out[str(i)]=o
pathlib.Path('tmp_portsmouth_audit/kaltura_probe.json').write_text(json.dumps(out,indent=2))
for k,v in out.items():
 print(k,v.get('http'),v.get('size'),len(v.get('kaltura_ids',[])),{z.split('_',1)[-1]:w['n'] for z,w in v.items() if z.startswith('term_')},flush=True)
