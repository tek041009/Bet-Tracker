import requests,re,json,pathlib,html
from urllib.parse import urljoin
O=pathlib.Path('tmp_portsmouth_audit');O.mkdir(exist_ok=True)
urls={
"SKY_MATCH":"https://www.skysports.com/football/west-ham-united-vs-portsmouth/video/562188",
"SKY_VIDEO_ORIGINAL":"https://www.skysports.com/football/video/30998/13571012/carabao-cup-jarrod-bowens-deflected-curler-puts-west-ham-in-front-against-portsmouth",
"READWESTHAM":"https://readwestham.com/2026/08/08/watch-west-ham-vs-portsmouth-highlights/",
"WEAREWESTHAM":"https://wearewestham.com/match/1567418",
"GOALDIR":"https://www.goaldir.com/matches/212740/",
"REDDIT_RSS":"https://www.reddit.com/r/soccer/comments/1viy1u2/.rss",
}
patterns=[
"13571012","13571115","Bowen's deflected","Bowen&#39;s deflected","jwplayer","jwplatform",
"brightcove","kaltura","mp4","m3u8","video-id","videoId","videourl","videoUrl","videoSource","data-video","embed",
"playerConfig","player-config","video-player","videoPlayer","videojs","shaka","mp.streamamg","cloudfront",
"v.redd.it","reddit_video","youtube.com/embed","vidhost","streamable","_video",
]
out={}
for name,u in urls.items():
 try:
  r=requests.get(u,timeout=25,headers={'User-Agent':'Googlebot'})
  raw=r.text; text=html.unescape(raw)
  snippets={}
  for pat in patterns:
   m=list(re.finditer(re.escape(pat),text,re.I))
   if m:snippets[pat]={'n':len(m),'samples':[text[max(0,x.start()-350):min(len(text),x.end()+450)] for x in m[:3]]}
  urls=list(dict.fromkeys(re.findall(r'https?://[^ <>"\n\t\\]+',text)))
  relevant=[x for x in urls if any(t in x.lower() for t in ("m3u8",".mp4",".mpd","video","brightcove","v.redd.it","streamable","streamain","youtube","akamaized"))]
  out[name]={'url':r.url,'code':r.status_code,'chars':len(raw),'snippets':snippets,'embedded_links':relevant[:80]}
  print(name,r.status_code,'FOUND',[(k,v['n']) for k,v in snippets.items() if k in ('13571012','brightcove','mp4','m3u8','v.redd.it','video-id','data-video')],flush=True)
 except Exception as e:out[name]={'error':str(e)}
O.joinpath('SKY_EMBED_AUDIT.json').write_text(json.dumps(out,indent=2))
