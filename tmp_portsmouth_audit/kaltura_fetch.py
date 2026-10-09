import pathlib,subprocess,requests,json,re
from PIL import Image,ImageDraw
ROOT=pathlib.Path('tmp_portsmouth_audit'); ROOT.mkdir(exist_ok=True)
BASE='https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/{}/format/url/protocol/https'
IDS=['0_rf4zz7e8','0_obcxj8mw','0_8lrtnx1l','0_iplk1pvk','0_4nzutk25','0_5vq1ppvj','0_mx9haob8','0_rc5a8usz']
url='https://std-pre-prod.whufc.com/en/matches/mens-team/west-ham-united-fc-v-portsmouth-fc-league-cup-20260808?tab=post-match'
page=requests.get(url,timeout=15).text
report={}
for x in IDS:
 m=re.search(x,page)
 left=page[max(0,m.start()-220):m.start()] if m else ''
 right=page[m.end():m.end()+350] if m else ''
 report[x]={'context_before':left,'context_after':right}
 u=BASE.format(x)
 try:
  r=requests.get(u,timeout=20,stream=True)
  report[x]['http_status']=r.status_code
  report[x]['final_url']=r.url
  report[x]['content_type']=r.headers.get('Content-Type')
  report[x]['content_length']=r.headers.get('Content-Length')
  report[x]['head_bytes']=next(r.iter_content(256),b'')[:256].decode('utf-8',errors='replace')
  r.close()
 except Exception as e:report[x]['error']=str(e)
 if x not in ('0_4nzutk25','0_iplk1pvk'):continue
 for source in [u,'kaltura:3000379:'+x]:
  try:
   cmd=['yt-dlp','--no-progress','--no-warnings','--socket-timeout','20','--retries','1',
       '-f','bv*[height<=720]+ba/b[height<=720]/best','--merge-output-format','mp4',
       '-o',f'/tmp/CLUB_{x}.%(ext)s',source]
   proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=120)
   report[x]['yt_dlp_'+source[:16]]=proc.stdout[-1600:]
  except Exception as e:report[x]['yt_dlp_error']=str(e)
  if list(pathlib.Path('/tmp').glob('CLUB_'+x+'.*')):break
 files=sorted(pathlib.Path('/tmp').glob('CLUB_'+x+'.*'),key=lambda f:f.stat().st_size,reverse=True)
 if files:
  p=files[0];report[x]['download_bytes']=p.stat().st_size
  d=pathlib.Path('/tmp')/('frames_CLUB_'+x);d.mkdir(exist_ok=True)
  proc=subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(p),'-t','140','-vf','fps=1,scale=480:-2','-q:v','5',str(d/'frame_%03d.jpg'),'-y'],capture_output=True,text=True,timeout=140)
  imgs=sorted(d.glob('*.jpg'));report[x]['frames']=len(imgs);report[x]['ffmpeg_result']=proc.stderr[-600:]
  for k in range(0,len(imgs),12):
   sh=Image.new('RGB',(1920,864),(25,25,25));draw=ImageDraw.Draw(sh)
   for idx,fn in enumerate(imgs[k:k+12]):
    im=Image.open(fn).convert('RGB');im.thumbnail((480,260))
    X=(idx%4)*480;Y=(idx//4)*288
    sh.paste(im,(X,Y+27))
    ts=k+idx
    draw.text((X+9,Y+7),f'{x}  {ts//60:02d}:{ts%60:02d}',fill='white')
   sh.save(ROOT/f'CLUB_{x}_SHEET_{k//12+1:02d}.jpg',quality=78,optimize=True)
with open(ROOT/'kaltura_results.json','w') as f:json.dump(report,f,indent=2)
for k,v in report.items():print(k,'title context',v['context_before'][-120:], 'HTTP',v.get('http_status'),'DL',v.get('download_bytes'), 'frames',v.get('frames'),flush=True)
