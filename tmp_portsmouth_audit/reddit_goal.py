import requests,re,json,pathlib,html,subprocess
from PIL import Image,ImageDraw
out=pathlib.Path('tmp_portsmouth_audit');out.mkdir(exist_ok=True)
url='https://www.reddit.com/r/soccer/comments/1viy1u2/.rss'
r=requests.get(url,timeout=20,headers={'User-Agent':'Mozilla/5.0'})
feed=html.unescape(r.text)
urls=list(dict.fromkeys(re.findall(r'https?://[^ <>"\n\r\t\\]+',feed)))
hrefs=[u for u in urls if any(z in u for z in ('v.redd.it','streamable','streamain','dubz','streamin','clippit','streamwo','youtube','streamja','streamff'))]
reddit_report={'feed_status':r.status_code,'rss_links':hrefs[:90],'feed_video_id':'2dg62yo806ih1'}
id='2dg62yo806ih1'
variants=[
 'https://v.redd.it/'+id+'/DASH_1080.mp4',
 'https://v.redd.it/'+id+'/DASH_720.mp4',
 'https://v.redd.it/'+id+'/DASH_480.mp4',
 'https://v.redd.it/'+id+'/DASH_360.mp4',
 'https://v.redd.it/'+id+'/DASHPlaylist.mpd',
 'https://v.redd.it/'+id+'/HLSPlaylist.m3u8',
 'https://v.redd.it/'+id+'/DASH_audio.mp4']
reddit_report['variants']={}
selected=None
for v in variants:
 try:
  q=requests.get(v,timeout=25,stream=True,headers={'User-Agent':'Mozilla/5.0'},allow_redirects=True)
  reddit_report['variants'][v]={'status':q.status_code,'type':q.headers.get('Content-Type'),'length':q.headers.get('Content-Length'),'final':q.url[:200]}
  print(v,'=>',q.status_code,q.headers.get('Content-Type'),q.headers.get('Content-Length'),flush=True)
  if q.status_code==200 and v.endswith('.mp4') and 'DASH_' in v and 'audio' not in v and selected is None:
   destination=pathlib.Path('/tmp/REDDIT_BOWEN_GOAL.mp4')
   with destination.open('wb') as f:
    for chunk in q.iter_content(chunk_size=1048576):
     if chunk:f.write(chunk)
   selected=destination
  q.close()
 except Exception as e:reddit_report['variants'][v]={'error':str(e)}
if selected:
  reddit_report['selected_bytes']=selected.stat().st_size
  p=subprocess.run(['ffprobe','-hide_banner','-loglevel','error','-show_entries','format=duration,size:stream=codec_type,width,height,r_frame_rate','-of','json',str(selected)],capture_output=True,text=True)
  reddit_report['metadata']=p.stdout[:3000]
  framesdir=pathlib.Path('/tmp/reddit_frames');framesdir.mkdir(exist_ok=True)
  cmd=['ffmpeg','-hide_banner','-loglevel','error','-i',str(selected),'-t','100','-vf','fps=2,scale=560:-2','-q:v','3',str(framesdir/'frame_%03d.jpg'),'-y']
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=100);reddit_report['ffmpeg_result']=p.stderr[-900:]
  pics=sorted(framesdir.glob('*.jpg'));reddit_report['frame_count']=len(pics)
  for j in range(0,len(pics),12):
   canvas=Image.new('RGB',(2240,1020),(30,30,30));d=ImageDraw.Draw(canvas)
   for i,fn in enumerate(pics[j:j+12]):
    im=Image.open(fn).convert('RGB');im.thumbnail((560,310))
    X=i%4*560;Y=i//4*340
    canvas.paste(im,(X,Y+30))
    t=(j+i)*.5
    d.text((X+9,Y+8),f'REDDIT  {int(t//60):02d}:{t%60:05.2f}',fill='white')
   canvas.save(out/f'REDDIT_ANGLE_{j//12+1:02d}.jpg',quality=84,optimize=True)
out.joinpath('REDDIT_GOAL_AUDIT.json').write_text(json.dumps(reddit_report,indent=2))
print('RESULT',json.dumps({'selected_bytes':reddit_report.get('selected_bytes'),'frames':reddit_report.get('frame_count'),'first_hrefs':hrefs[:30]}),flush=True)
