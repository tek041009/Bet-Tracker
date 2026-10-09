import pathlib,subprocess
from PIL import Image, ImageDraw
ROOT=pathlib.Path('tmp_portsmouth_audit');ROOT.mkdir(exist_ok=True)
tag='0_iplk1pvk';url='https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/'+tag+'/format/url/protocol/https'
cmd=['yt-dlp','--no-progress','--no-warnings','--socket-timeout','20','--retries','1','--merge-output-format','mp4','-o','/tmp/EXTENDED_FULL.%(ext)s',url]
print('DOWNLOAD_EXTENDED',flush=True)
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=130)
print(r.stdout[-600:],flush=True)
files=list(pathlib.Path('/tmp').glob('EXTENDED_FULL.*'))
assert files,'Extended footage download failed'
p=files[0];frame_dir=pathlib.Path('/tmp/extended_goal_images');frame_dir.mkdir(exist_ok=True)
start=125;dur=105
cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(p),'-t',str(dur),'-vf','fps=1,scale=480:-2','-q:v','4',str(frame_dir/'frame_%03d.jpg'),'-y']
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=150)
pics=sorted(frame_dir.glob('*.jpg')); print('FRAMES',len(pics),'errors',r.stderr[-300:],flush=True)
for k in range(0,len(pics),12):
 chunk=pics[k:k+12];sh=Image.new('RGB',(1920,864),(25,25,25));d=ImageDraw.Draw(sh)
 for i,fn in enumerate(chunk):
  im=Image.open(fn).convert('RGB');im.thumbnail((480,260))
  x=(i%4)*480;y=(i//4)*288
  sh.paste(im,(x,y+27))
  t=start+k+i
  d.text((x+7,y+7),f'EXTENDED  {t//60:02d}:{t%60:02d}',fill='white')
 sh.save(ROOT/f'EXTENDED_GOAL_SHEET_{k//12+1:02d}.jpg',quality=82,optimize=True)
ROOT.joinpath('extended_result.txt').write_text(f'URL {url}\nSOURCE_BYTES {p.stat().st_size}\nCAPTURED_FRAMES {len(pics)}\nSTART 125\nDURATION 105\n')
