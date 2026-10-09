import pathlib,subprocess,json
from PIL import Image,ImageDraw
root=pathlib.Path('tmp_portsmouth_audit')
video_id='0_iplk1pvk'
url='https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/'+video_id+'/format/url/protocol/https'
output=pathlib.Path('/tmp/visual_source.%(ext)s')
cmd=['yt-dlp','--no-progress','--no-warnings','--socket-timeout','25','--retries','1','-f','b','-o',str(output),url]
r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=140)
sources=list(pathlib.Path('/tmp').glob('visual_source.*'))
assert sources, r.stdout[-1000:]
video=max(sources,key=lambda p:p.stat().st_size)
meta=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration,size,bit_rate:stream=index,codec_type,width,height,r_frame_rate','-of','json',str(video)],capture_output=True,text=True,timeout=20)
(root/'source_metadata.json').write_text(meta.stdout)
for name,t0,t1 in [('ORIGINAL_SHOT',155.5,161.6),('CELEBRATION',162.5,168.4),('REPLAY_FRONT',171.5,177.7),('REPLAY_SIDELINE',177.6,183.6),('REPLAY_BEHIND_NET',183.0,189.6)]:
 outdir=pathlib.Path('/tmp')/('key_frames_'+name);outdir.mkdir(exist_ok=True)
 command=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(t0),'-i',str(video),'-t',str(t1-t0),'-vf','fps=4,scale=560:-2','-q:v','3',str(outdir/'frame_%03d.jpg'),'-y']
 p=subprocess.run(command,capture_output=True,text=True,timeout=110)
 frames=sorted(outdir.glob('*.jpg'))
 print(name,'FRAMES',len(frames),p.stderr[-100:],flush=True)
 for k in range(0,len(frames),12):
  canvas=Image.new('RGB',(2240,1020),(30,30,30));d=ImageDraw.Draw(canvas)
  for i,f in enumerate(frames[k:k+12]):
   im=Image.open(f).convert('RGB');im.thumbnail((560,310))
   x=(i%4)*560;y=(i//4)*340
   canvas.paste(im,(x,y+30))
   abs_t=t0+(k+i)/4
   d.text((x+9,y+8),f'{name} {int(abs_t//60):02d}:{abs_t%60:05.2f}',fill='white')
  canvas.save(root/f'REFINED_{name}_{k//12+1:02d}.jpg',quality=85,optimize=True)
