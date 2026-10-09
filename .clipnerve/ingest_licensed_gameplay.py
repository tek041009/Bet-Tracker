#!/usr/bin/env python3
"""ClipNerve CC-BY gameplay acquisition: hash-verified source, QA-only transcode."""
import hashlib, subprocess
from pathlib import Path
url="https://upload.wikimedia.org/wikipedia/commons/c/cf/PAC-MAN_256_-_Let%27s_Play_%28gameplay%29.webm"
subprocess.run(["curl","-fL","--retry","3","--max-time","480",url,"-o","gameplay_source.webm"],check=True)
p=Path("gameplay_source.webm")
sha=hashlib.sha1(p.read_bytes()).hexdigest()
assert p.stat().st_size==116829012 and sha=="57af1c458abfd557864a07da36a8483924e8afc8", (p.stat().st_size,sha)
print("VERIFIED_CC_BY_SOURCE_SHA1="+sha,flush=True)
subprocess.run(["ffmpeg","-y","-v","error","-ss","18","-i",str(p),"-t","28","-vf","scale=1080:608,setsar=1","-an","-c:v","libx264","-preset","veryfast","-crf","20","-movflags","+faststart","clipnerve_licensed_gameplay_sample.mp4"],check=True)
print("SOURCE_PREVIEW_BYTES="+str(Path("clipnerve_licensed_gameplay_sample.mp4").stat().st_size),flush=True)
