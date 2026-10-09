import pathlib, subprocess, json, re, requests
from PIL import Image,ImageDraw
ROOT=pathlib.Path('tmp_portsmouth_audit');ROOT.mkdir(exist_ok=True)
sources={
'SKY_GOAL':'https://www.skysports.com/football/video/30998/13571012/carabao-cup-jarrod-bowens-deflected-curler-puts-west-ham-in-front-against-portsmouth',
'SKY_HIGHLIGHTS':'https://www.skysports.com/football/video/30998/13571115/west-ham-united-3-1-portsmouth-carabao-cup-highlights',
'REDDIT_GOAL':'https://www.reddit.com/r/soccer/comments/1viy1u2/west_ham_united_21_portsmouth_jarrod_bowen_45_efl/',
'WHU_MATCH_CENTRE':'https://std-pre-prod.whufc.com/en/matches/mens-team/west-ham-united-fc-v-portsmouth-fc-league-cup-20260808?tab=pre-match',
}
report={}
for name,url in sources.items():
    print('ANALYZE',name,flush=True)
    q={}
    try:
        r=requests.get(url,timeout=15,headers={'User-Agent':'Mozilla/5.0'})
        body=r.text
        q['http_status']=r.status_code
        q['html_length']=len(body)
        q['html_evidence']=[body[max(0,m.start()-100):m.end()+140] for m in list(re.finditer('m3u8|mp4|brightcove|kaltura|videoId|video_id|playerId|jwplayer|dash|replay',body,re.I))[:20]]
    except Exception as e:q['http_error']=str(e)
    cmd=['yt-dlp','--no-playlist','--no-progress','--no-warnings','--socket-timeout','15','--retries','1',
         '-f','bv*[height<=720]+ba/b[height<=720]/best','--merge-output-format','mp4',
         '-o','/tmp/'+name+'.%(ext)s',url]
    try:
        proc=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        q['extractor_log']=proc.stdout[-5000:]
    except Exception as e:q['extractor_log']='EXCEPTION '+str(e)
    f=sorted(pathlib.Path('/tmp').glob(name+'.*'),key=lambda p:p.stat().st_size,reverse=True)
    if f:
        p=f[0];q['downloaded_bytes']=p.stat().st_size
        frames_dir=pathlib.Path('/tmp')/('frames_'+name);frames_dir.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(p),'-t','60',
          '-vf','fps=1,scale=480:-2','-q:v','5',str(frames_dir/'frame_%03d.jpg'),'-y'],
          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        pics=sorted(frames_dir.glob('*.jpg'))
        q['frames']=len(pics)
        for k in range(0,len(pics),12):
            sh=Image.new('RGB',(1920,864),(25,25,25))
            d=ImageDraw.Draw(sh)
            for idx,fm in enumerate(pics[k:k+12]):
                im=Image.open(fm).convert('RGB');im.thumbnail((480,260))
                x=(idx%4)*480;y=(idx//4)*288
                sh.paste(im,(x,y+27));d.text((x+10,y+7),f'{name}  00:{k+idx:02d}',fill=(255,255,255))
            sh.save(ROOT/f'{name}_{k//12+1:02d}.jpg',quality=75,optimize=True)
    report[name]=q
with open(ROOT/'sky_results.json','w') as f:json.dump(report,f,indent=2)
for name,info in report.items():print(name,'HTTP',info.get('http_status'),'download',info.get('downloaded_bytes'),'result',str(info.get('extractor_log',''))[-700:],flush=True)
