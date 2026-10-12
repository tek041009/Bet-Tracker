import subprocess,json,pathlib,re
from PIL import Image, ImageDraw
O=pathlib.Path('tmp_portsmouth_audit');O.mkdir(exist_ok=True)
url='https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/0_iplk1pvk/format/applehttp/protocol/https'
result={'source':url}
cmd=['yt-dlp','--no-progress','--no-warnings','--no-playlist','--socket-timeout','25','--retries','1',
     '-f','best[height<=1080]','-o','/tmp/WESTHAM_1080.%(ext)s',url]
try:
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=235)
 result['download_exit']=p.returncode
 result['download_log']=(p.stdout+'\n'+p.stderr)[-1800:]
except Exception as e:result['download_error']=str(e)
videos=sorted([p for p in pathlib.Path('/tmp').glob('WESTHAM_1080.*') if p.stat().st_size>1000000],key=lambda f:f.stat().st_size,reverse=True)
if videos:
 v=videos[0]; result['original_bytes']=v.stat().st_size
 p=subprocess.run(['ffmpeg','-hide_banner','-i',str(v)],capture_output=True,text=True,timeout=25)
 result['metadata']=p.stderr[-2600:]
 t0=151;length=39
 fd=pathlib.Path('/tmp/WHU_1080_frames');fd.mkdir(exist_ok=True)
 cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(t0),'-i',str(v),'-t',str(length),'-vf','fps=2,scale=640:-2','-q:v','4',str(fd/'f_%03d.jpg'),'-y']
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=135)
  result['frames_extract_error']=p.stderr[-500:]
 except Exception as e:result['frames_extract_error']=str(e)
 pics=sorted(fd.glob('f_*.jpg'));result['frames']=len(pics)
 for k in range(0,len(pics),12):
  sh=Image.new('RGB',(2560,1152),(25,25,25));draw=ImageDraw.Draw(sh)
  for i,fn in enumerate(pics[k:k+12]):
   im=Image.open(fn).convert('RGB');im.thumbnail((640,357))
   x=(i%4)*640;y=(i//4)*384;sh.paste(im,(x,y+27))
   sec=t0+(k+i)/2
   draw.text((x+10,y+7),f'WHU1080  {int(sec//60):02d}:{sec%60:05.2f}',fill='white')
  sh.save(O/f'WHU_HIGH_QUALITY_{k//12+1:02d}.jpg',quality=82,optimize=True)
O.joinpath('WHU_1080_AUDIT.json').write_text(json.dumps(result,indent=2))
print('FINISHED',json.dumps({k:v for k,v in result.items() if k not in ('download_log','metadata')}),flush=True)
