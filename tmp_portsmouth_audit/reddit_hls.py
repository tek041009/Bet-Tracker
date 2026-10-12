import requests,subprocess,json,pathlib,html,re
from PIL import Image,ImageDraw
O=pathlib.Path('tmp_portsmouth_audit');O.mkdir(exist_ok=True)
base='https://v.redd.it/2dg62yo806ih1/'
rep={}
for tail in ['HLSPlaylist.m3u8','DASHPlaylist.mpd','DASH_720.mp4','HLS_720.m3u8','HLS_360.m3u8','DASH_1080.mp4']:
 url=base+tail
 try:
  r=requests.get(url,timeout=20,headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.reddit.com/"})
  rep[tail]={'code':r.status_code,'type':r.headers.get('Content-Type'),'body':r.text[:6500] if len(r.content)<15000 else '<large>','length':len(r.content)}
 except Exception as e:rep[tail]={'error':str(e)}
files=[]
for tool in [['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',base+'HLSPlaylist.m3u8','-c','copy','/tmp/RED_HLS.mp4'],
             ['yt-dlp','--no-progress','--no-warnings','--socket-timeout','20','--retries','1','-o','/tmp/RED_YTDLP.%(ext)s',base+'HLSPlaylist.m3u8'],
             ['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',base+'DASHPlaylist.mpd','-c','copy','/tmp/RED_DASH.mp4']]:
 try:
  p=subprocess.run(tool,capture_output=True,text=True,timeout=105)
  rep['tool_'+tool[0]+'_'+tool[-1][:10]]={'exit':p.returncode,'stdout':p.stdout[-1500:],'stderr':p.stderr[-1500:]}
 except Exception as e:rep['tool_'+tool[0]+'_'+tool[-1][:10]]={'error':str(e)}
files=[p for prefix in ('RED_HLS','RED_YTDLP','RED_DASH') for p in pathlib.Path('/tmp').glob(prefix+'.*') if p.stat().st_size>100000]
for p in files:
 vid=pathlib.Path('/tmp')/'red_frames';vid.mkdir(exist_ok=True)
 probe=subprocess.run(['ffmpeg','-hide_banner','-i',str(p)],capture_output=True,text=True)
 rep['metadata_'+p.name]=probe.stderr[-2500:]
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(p),'-t','70','-vf','fps=2,scale=560:-2','-q:v','4',str(vid/'f_%03d.jpg'),'-y'],capture_output=True,text=True,timeout=90)
 pics=sorted(vid.glob('f_*.jpg'))
 rep['frames_'+p.name]=len(pics)
 for k in range(0,len(pics),12):
  sh=Image.new('RGB',(2240,1020),(24,24,24));d=ImageDraw.Draw(sh)
  for i,fn in enumerate(pics[k:k+12]):
   im=Image.open(fn);im.thumbnail((560,310));X=(i%4)*560;Y=(i//4)*340;sh.paste(im,(X,Y+30))
   t=(k+i)/2;d.text((X+8,Y+6),f'REDDIT {t:05.1f}',fill='white')
  sh.save(O/f'REDDIT_HLS_SHEET_{k//12+1:02d}.jpg',quality=79,optimize=True)
 break
O.joinpath('REDDIT_HLS_REPORT.json').write_text(json.dumps(rep,indent=2))
for k,v in rep.items():print(k,v.get('code'),v.get('exit'),v.get('length'),v.get('body','')[:140],flush=True)
