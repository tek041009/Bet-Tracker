#!/usr/bin/env python3
"""Cut-only mute Portsmouth sequence, approved V77 untouched. All six shots are SOURCE trims."""
from pathlib import Path
import subprocess, json, shutil
from PIL import Image,ImageDraw

ROOT=Path("tmp_portsmouth_audit")
OUTPUT=ROOT/"PORTSMOUTH_ONLY_SIX_SHOTS_SILENT_PREVIEW.mp4"
TEMP=Path("/tmp/portsmouth_video_source")
TEMP.mkdir(exist_ok=True)
url_w="https://open.http.mp.streamamg.com/p/3000379/sp/300037900/playManifest/entryId/0_iplk1pvk/format/applehttp/protocol/https"
url_s="https://v.redd.it/2dg62yo806ih1/HLSPlaylist.m3u8"

def cmd(args, timeout=240):
    print("RUN", " ".join(str(x) for x in args)[:400], flush=True)
    x=subprocess.run([str(a) for a in args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    print("RESULT",x.returncode,x.stdout[-800:],flush=True)
    if x.returncode: raise RuntimeError(x.stdout[-2000:])
    return x

whu=TEMP/"WEST_HAM_1080.mp4"
sky=TEMP/"SKY_REDDIT_720.mp4"
cmd(["yt-dlp","--no-progress","--no-warnings","--socket-timeout","30","--retries","2","-f","best[height<=1080]","-o",str(whu),url_w],timeout=250)
cmd(["yt-dlp","--no-progress","--no-warnings","--socket-timeout","30","--retries","2","-o",str(sky),url_s],timeout=180)
assert whu.stat().st_size>100_000_000,(whu.stat().st_size)
assert sky.stat().st_size>5_000_000,(sky.stat().st_size)
print("SOURCE_BYTES",whu.stat().st_size,sky.stat().st_size,flush=True)

SHOTS=[
    ("01_Build_up_live_wide",whu,154.30,157.80,"West Ham 1080p match broadcast"),
    ("02_Bowen_technique_tight_sideline",whu,180.10,181.60,"West Ham 1080p sideline replay"),
    ("03_Ball_flight_goal",whu,158.45,160.65,"West Ham 1080p match broadcast"),
    ("04_Bowen_first_celebration",whu,163.50,166.70,"West Ham 1080p close celebration"),
    ("05_Team_huddle",sky,19.60,21.40,"Sky Sports 720p broadcast"),
    ("06_Bowen_smiles",sky,30.00,31.50,"Sky Sports 720p broadcast")
]

manifest=[]
concatlist=TEMP/"shots.txt"
for n,(label,path,t0,t1,source) in enumerate(SHOTS,1):
    dest=TEMP/f"{n:02d}.mp4"
    # Pure trim, 25-fps normal playback, uniform output; no audio, no music, no effects or transitions.
    args=["ffmpeg","-hide_banner","-loglevel","warning","-y","-ss",f"{t0:.3f}","-i",path,
          "-t",f"{t1-t0:.3f}","-an","-vf","fps=25,scale=1920:1080:flags=lanczos,setsar=1,format=yuv420p",
          "-c:v","libx264","-preset","fast","-crf","22","-pix_fmt","yuv420p",
          "-video_track_timescale","25000","-movflags","+faststart",dest]
    cmd(args,timeout=130)
    manifest.append({"shot":n,"label":label,"source":source,"source_in":t0,"source_out":t1,
                     "duration":round(t1-t0,3),"segment_bytes":dest.stat().st_size})
concatlist.write_text("".join("file '"+str((TEMP/f'{i:02d}.mp4').resolve())+"'\n" for i in range(1,len(SHOTS)+1)))
cmd(["ffmpeg","-hide_banner","-loglevel","warning","-y","-f","concat","-safe","0","-i",concatlist,
     "-c","copy","-an","-movflags","+faststart",OUTPUT],timeout=90)
assert OUTPUT.stat().st_size>1_000_000,OUTPUT.stat().st_size
print("PREVIEW_CREATED",OUTPUT,str(OUTPUT.stat().st_size),flush=True)

# Inspect actual rendered video, not just source: 2Hz contact sheets.
QA=ROOT/"PORTSMOUTH_SILENT_QA"
QA.mkdir(exist_ok=True)
for x in QA.glob("*.jpg"):x.unlink()
frames=TEMP/"finished_frames";frames.mkdir(exist_ok=True)
cmd(["ffmpeg","-hide_banner","-loglevel","error","-y","-i",OUTPUT,
    "-vf","fps=2,scale=640:-2","-q:v","3",str(frames/"f_%03d.jpg")],timeout=100)
pics=sorted(frames.glob("*.jpg"))
for chunkidx in range(0,len(pics),12):
    sheet=Image.new("RGB",(2560,1152),(25,25,25));draw=ImageDraw.Draw(sheet)
    for index,f in enumerate(pics[chunkidx:chunkidx+12]):
        frame=Image.open(f).convert("RGB");frame.thumbnail((640,358))
        x=index%4*640;y=index//4*384
        sheet.paste(frame,(x,y+26))
        t=(chunkidx+index)/2
        draw.text((x+10,y+5),f"SILENT FINAL RENDER   {t:05.1f}s",fill="white")
    sheet.save(QA/f"QA_{chunkidx//12+1:02d}.jpg",quality=77,optimize=True)
(ROOT/"PORTSMOUTH_SILENT_SHOT_LEDGER.json").write_text(json.dumps({
    "output":str(OUTPUT),"output_bytes":OUTPUT.stat().st_size,
    "video_only":True,"audio_tracks":0,"music":False,"no_effects":True,
    "source_whu_bytes":whu.stat().st_size,"source_sky_bytes":sky.stat().st_size,
    "shots":manifest,"total_nominal_duration":round(sum(s["duration"] for s in manifest),3),
    "qa_frames":len(pics)
},indent=2))
print("RENDER_QA_READY",len(pics),"QA sheets",len(list(QA.glob("*.jpg"))),flush=True)
