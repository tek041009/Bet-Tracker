"""ClipNerve offline Reddit QA source verifier."""
from pathlib import Path
import hashlib, subprocess
URL="https://upload.wikimedia.org/wikipedia/commons/c/cf/PAC-MAN_256_-_Let%27s_Play_%28gameplay%29.webm"
SHA1="57af1c458abfd557864a07da36a8483924e8afc8"
SIZE=116829012
def run(*cmd):
    subprocess.run(list(cmd),check=True)
def source():
    p=Path("licensed_pacman256_1080p.webm")
    run("curl","-fL","--retry","3","--max-time","540",URL,"-o",str(p))
    assert p.stat().st_size==SIZE
    assert hashlib.sha1(p.read_bytes()).hexdigest()==SHA1
    return p
