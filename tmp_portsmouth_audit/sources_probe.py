import requests,json,time,concurrent.futures,traceback,re
from pathlib import Path
out=Path('tmp_portsmouth_audit')
out.mkdir(exist_ok=True)
base='https://www.reddit.com/r/soccer/comments/1viy1u2/'
tests = {
'sky_16472':"https://www.skysports.com/football/video/16472/13571012/carabao-cup-jarrod-bowens-deflected-curler-puts-west-ham-in-front-against-portsmouth",
'sky_no_category':"https://www.skysports.com/football/video/13571012/carabao-cup-jarrod-bowens-deflected-curler-puts-west-ham-in-front-against-portsmouth",
'sky_match':"https://www.skysports.com/football/west-ham-united-vs-portsmouth/video/562188",
'sky_mobile':"https://m.skysports.com/football/video/30998/13571012/carabao-cup-jarrod-bowens-deflected-curler-puts-west-ham-in-front-against-portsmouth",
'sky_16472_full':"https://www.skysports.com/football/video/16472/13571115/west-ham-united-3-1-portsmouth-carabao-cup-highlights",
'sky_mobilevideo':"https://www.skysports.com/football/video/30998/13571012",
'reddit_old':"https://old.reddit.com/r/soccer/comments/1viy1u2/west_ham_united_21_portsmouth_jarrod_bowen_45_efl/",
'reddit_json':base+'.json?raw_json=1',
'reddit_api':"https://api.reddit.com/r/soccer/comments/1viy1u2?raw_json=1",
'reddit_rss':base+'.rss',
'reddit_www':base,
'reddit_embed':"https://www.redditmedia.com/r/soccer/comments/1viy1u2/",
'reddit_new':"https://www.reddit.com/comments/1viy1u2.json",
'streams_pipedapi_kavin':'https://pipedapi.kavin.rocks/streams/ILZR4ngvWfE',
'streams_pipedapi_leptons':'https://pipedapi.leptons.xyz/streams/ILZR4ngvWfE',
'streams_pipedapi_adminforge':'https://pipedapi.adminforge.de/streams/ILZR4ngvWfE',
'streams_pipedapi_yt':'https://api.piped.yt/streams/ILZR4ngvWfE',
'streams_pipedapi_ducks':'https://pipedapi.ducks.party/streams/ILZR4ngvWfE',
'streams_pipedapi_privacy':'https://api.piped.private.coffee/streams/ILZR4ngvWfE',
'streams_pipedapi_drgns':'https://pipedapi.drgns.space/streams/ILZR4ngvWfE',
'streams_pipedapi_codespace':'https://piped-api.codespace.cz/streams/ILZR4ngvWfE',
'streams_invidious_nadeko':'https://inv.nadeko.net/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_yewtu':'https://yewtu.be/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_privatecoffee':'https://invidious.private.coffee/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_tux':'https://inv.tux.pizza/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_artemis':'https://yt.artemislena.eu/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_protokolla':'https://invidious.protokolla.fi/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_melmac':'https://iv.melmac.space/api/v1/videos/ILZR4ngvWfE',
'streams_invidious_ytclub':'https://yt.drgnz.club/api/v1/videos/ILZR4ngvWfE',
'youtube_embed':'https://www.youtube-nocookie.com/embed/ILZR4ngvWfE',
'streamain_search':'https://streamain.com/en/search?q=West%20Ham%20Portsmouth%20Bowen',
}
def check(item):
 name,url=item
 try:
  r=requests.get(url,timeout=17,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36", "Accept":"text/html,application/json,*/*"},allow_redirects=True)
  t=r.text
  v={'status':r.status_code,'type':r.headers.get('Content-Type'),'len':len(r.content),'url':r.url[:250],'start':t[:500],'interesting_links':re.findall(r'(?:https?[^" <\\\\]+(?:\.m3u8|\.mp4|\.mpd))',t)[:6]}
  if 'json' in r.headers.get('Content-Type','') and len(t)<5000000:
   try:
    j=r.json()
    v['json_keys']=list(j.keys()) if isinstance(j,dict) else ['array']
    if isinstance(j,dict):
     for key in ('title','message','error','videoStreams','audioStreams','formatStreams','adaptiveFormats','requestedFormats','hlsUrl','dashUrl','videoId'):
      if key in j:
       val=j[key]
       if isinstance(val,list):v[key]=val[:3]
       else:v[key]=val
   except Exception as e:v['parse_error']=str(e)
  if ('reddit' in name and r.status_code==200):v['reddit_embeds']=re.findall(r'(?:https?[^" <\\\\]+(?:v\.redd\.it|streamable|streamain|dubz|clippit)[^" <\\\\]{0,120})',t,re.I)[:30]
  return name,v
 except Exception as e:return name,{'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
  for name,v in ex.map(check,tests.items()):
   print(name, 'STATUS',v.get('status'),v.get('error',''),'size',v.get('len'),'JSON',v.get('json_keys'),flush=True)
   tests[name]=v
(out/'OTHER_SOURCES_PROBE.json').write_text(json.dumps(tests,indent=2,default=str))
