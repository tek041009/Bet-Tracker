import os, subprocess, sys, pathlib, json, textwrap
from PIL import Image, ImageDraw
ROOT=pathlib.Path('tmp_portsmouth_audit')
ROOT.mkdir(exist_ok=True)
SRC={
'WHU_EXTENDED':('B5_vpCdI57E',138,195),
'EFL_EXTENDED':('ILZR4ngvWfE',125,182),
'WHU_SHORT':('R15cQiru4-U',50,99),
'EFL_CONDENSED':('7oEhDOc7GXE',0,None),
'SCTV':('Syig5LWe0d4',0,None),
}
status={}
for name,(vid,start,end) in SRC.items():
    output=f'/tmp/{name}.%(ext)s'
    cmd=['yt-dlp','--no-playlist','--no-warnings','--no-progress','--no-check-certificate',
         '--socket-timeout','20','--retries','2','--concurrent-fragments','2',
         '-f','bv*[height<=720]+ba/b[height<=720]/best',
         '--merge-output-format','mp4','-o',output,'https://www.youtube.com/watch?v='+vid]
    print('BEGIN_DOWNLOAD',name,flush=True)
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=140)
    vids=list(pathlib.Path('/tmp').glob(name+'.*'))
    if not vids:
        status[name]={'download':'failed','log':proc.stdout[-1700:]}
        print('FAILED',name,proc.stdout[-1500:],flush=True)
        continue
    p=max(vids,key=lambda f:f.stat().st_size)
    frames_dir=pathlib.Path('/tmp')/('frames_'+name)
    frames_dir.mkdir(exist_ok=True)
    dur=60 if end is None else end-start
    # Absolute source timestamp encoded into each frame label for editorial use.
    args=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(p),
          '-t',str(dur),'-vf','fps=1,scale=480:-2','-q:v','5',
          str(frames_dir/'frame_%03d.jpg'),'-y']
    capture=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=100)
    pics=sorted(frames_dir.glob('*.jpg'))
    status[name]={'download':'ok','filename':p.name,'bytes':p.stat().st_size,
                  'start':start,'duration':dur,'frames':len(pics),'ffmpeg':capture.stdout[-350:]}
    if not pics: continue
    for k in range(0,len(pics),12):
        chunk=pics[k:k+12]
        w,h=480,288
        sheet=Image.new('RGB',(w*4,h*3),(23,23,23))
        draw=ImageDraw.Draw(sheet)
        for idx,frame in enumerate(chunk):
            im=Image.open(frame).convert('RGB')
            im.thumbnail((w,h-27))
            x=(idx%4)*w
            y=(idx//4)*h
            sheet.paste(im,(x,y+27))
            ts=start+k+idx
            draw.text((x+10,y+7),f'{name}  {ts//60:02d}:{ts%60:02d}',fill=(255,255,255))
        sheet.save(ROOT/(f'{name}_{k//12+1:02d}.jpg'),quality=75,optimize=True)
    print('SUCCESS',name,len(pics),flush=True)
with open(ROOT/'results.json','w') as f:json.dump(status,f,indent=2)
print('RESULT_SUMMARY',json.dumps(status),flush=True)
