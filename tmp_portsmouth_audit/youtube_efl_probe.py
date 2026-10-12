import requests,subprocess,json,re,pathlib
O=pathlib.Path('tmp_portsmouth_audit');O.mkdir(exist_ok=True)
VID='ILZR4ngvWfE'
urls={'nocookie':f'https://www.youtube-nocookie.com/embed/{VID}','embed':f'https://www.youtube.com/embed/{VID}','watch':f'https://www.youtube.com/watch?v={VID}','music':f'https://music.youtube.com/watch?v={VID}'}
report={}
for name,url in urls.items():
 try:
  r=requests.get(url,timeout=18,headers={'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'})
  s=r.text
  obj={'code':r.status_code,'len':len(s),'login_req':bool(re.search('LOGIN_REQUIRED|confirm.you.re.not.a.bot',s,re.I))}
  for pattern in ['INNERTUBE_API_KEY','INNERTUBE_CONTEXT','ytInitialPlayerResponse','streamingData','storyboards','playerStoryboardSpecRenderer','playabilityStatus','playbackTracking','videoDetails','storyboard3_L','VISITOR_DATA','apiUrl','ytcfg.set']:
   m=list(re.finditer(pattern,s,re.I))
   obj[pattern]={'n':len(m),'example':[s[max(0,x.start()-100):x.end()+250] for x in m[:2]]}
  m=re.search(r'ytInitialPlayerResponse\s*=\s*(\{)',s)
  if m:
   st=m.end()-1;depth=0;in_str=False;esc=False;end=None
   for i,ch in enumerate(s[st:st+1000000]):
    if esc:esc=False;continue
    if ch=='\\' and in_str:esc=True;continue
    if ch=='"':in_str=not in_str;continue
    if in_str:continue
    if ch=='{':depth+=1
    elif ch=='}':
     depth-=1
     if depth==0:end=st+i+1;break
   if end:
    try:
     j=json.loads(s[st:end]);obj['PLAYER']={'status':j.get('playabilityStatus'),
      'videoTitle':j.get('videoDetails',{}).get('title'),
      'streamingKeys':list(j.get('streamingData',{}).keys()),
      'streamFormats':[{'mimeType':x.get('mimeType'),'quality':x.get('qualityLabel'),'url':x.get('url','')[:180]} for x in j.get('streamingData',{}).get('formats',[])[:10]],
      'storyboards':j.get('storyboards')}
    except Exception as e:obj['parse_error']=str(e)
  report[name]=obj
  print(name,r.status_code,'len',len(s),'player',obj.get('PLAYER',{}).get('status'),'board?',bool(obj.get('PLAYER',{}).get('storyboards')),flush=True)
 except Exception as e:report[name]={'error':str(e)}
# Quick check direct embed through yt-dlp with no account, probing only.
for client in ['web_embedded','android_vr','mweb','tv_embedded','web_safari','ios']:
 cmd=['yt-dlp','--no-warnings','--skip-download','--socket-timeout','12','--retries','0','--extractor-args',f'youtube:player_client={client}','-F',f'https://www.youtube.com/watch?v={VID}']
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=28)
  report['ytdlp_'+client]={'return':p.returncode,'tail':(p.stdout+'\n'+p.stderr)[-1800:]}
  print('client',client,'return',p.returncode,'summary',p.stderr[-120:],flush=True)
 except Exception as e:report['ytdlp_'+client]={'error':str(e)}
O.joinpath('YOUTUBE_EFL_PROBE.json').write_text(json.dumps(report,indent=2))
