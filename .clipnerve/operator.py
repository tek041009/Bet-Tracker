#!/usr/bin/env python3
"""ClipNerve's GitHub Actions FFmpeg job runner.

One immutable per-video JSON request triggers this existing runner.
Newly-rendered output defaults to QA_HOLD. Publication requires approval
of the exact rendered SHA-256 and source-rights/visual/audio evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

REPO = "tek041009/Bet-Tracker"
CHANNELS = {
    "tiktok": "6ac51f456a5c39ccb631eeaa",
    "youtube": "6ac6c6546a5c39ccb647acb5",
}
def run(args):
    subprocess.run(args, check=True)

def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()

def need(condition, reason):
    if not condition:
        raise ValueError(reason)

def probe(path):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=codec_name,width,height:format=duration",
        "-of", "json", str(path)
    ], text=True)
    d = json.loads(result)
    streams = d.get("streams", [])
    v = [s for s in streams if s.get("width")]
    a = [s for s in streams if s.get("codec_name") == "aac"]
    need(len(v) == 1 and v[0]["codec_name"] == "h264", "Video must be H264")
    need(v[0].get("width") == 1080 and v[0].get("height") == 1920, "Video must be 1080x1920")
    need(a, "Video needs real AAC audio")
    need(float(d["format"]["duration"]) > 1, "Video too short")
    return d

def quoted(s):
    return json.dumps(s, ensure_ascii=False)

def gql_post(job, url):
    name = job["platform"]
    meta = ("tiktok: {title: " + quoted(job["title"]) + ", isAiGenerated: " +
            str(bool(job.get("is_ai_generated", False))).lower() + "}"
            if name == "tiktok" else
            "youtube: {title: " + quoted(job["title"]) +
            ", categoryId: " + quoted(str(job.get("category_id", "24"))) +
            ", madeForKids: " + str(bool(job.get("made_for_kids", False))).lower() + "}")
    query = (
        "mutation { createPost(input: {text:" + quoted(job["caption"]) +
        ", channelId:" + quoted(CHANNELS[name]) +
        ", schedulingType: automatic, mode: " + job["buffer_mode"] +
        ", assets:[{video:{url:" + quoted(url) + "}}], metadata:{" + meta +
        "}}) { ... on PostActionSuccess {post{id status dueAt}} "
        "... on MutationError {message} } }"
    )
    token = os.environ.get("BUFFER_API_KEY")
    need(bool(token), "Buffer API key unavailable")
    req = urllib.request.Request(
        "https://api.buffer.com", data=json.dumps({"query":query}).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + token}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.load(resp)
    print("BUFFER_RESPONSE=" + json.dumps(result))
    need(not result.get("errors"), "Buffer GraphQL errors")
    output = (result.get("data") or {}).get("createPost") or {}
    need(not output.get("message"), "Buffer rejected: " + str(output.get("message")))
    posted = output.get("post") or {}
    need(bool(posted.get("id")), "No Buffer post ID returned")
    print("BUFFER_ACCEPTED_POST_ID=" + posted["id"])
    print("BUFFER_POST_STATUS=" + str(posted.get("status")))

def main(path):
    job = json.loads(Path(path).read_text())
    # Offline ASR verification of the ORIGINAL voice, not publication or synthesis.
    if job.get("mode") == "qa_asr":
        cid = job["clip_id"]
        need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{6,72}", cid)), "Invalid QA transcript id")
        url = job["audio_url"]
        need(url.startswith("https://dnznrvs05pmza.cloudfront.net/text_to_speech/"), "Unexpected audio source")
        source = Path("original_voice_" + cid + ".mp3")
        run(["curl", "-fL", "--retry", "2", "--connect-timeout", "30",
             "--max-time", "180", url, "-o", str(source)])
        # Use a dedicated venv: github ubuntu Python sometimes installs --user
        # packages outside the script interpreter's import path.
        venv = Path("/tmp/clipnerve_whisper_venv")
        run(["python3", "-m", "venv", str(venv)])
        run([str(venv/"bin/python"), "-m", "pip", "install", "-q", "faster-whisper==1.2.0"])
        pycode = """import json,sys
from faster_whisper import WhisperModel
model=WhisperModel('tiny.en',device='cpu',compute_type='int8')
segments,info=model.transcribe(sys.argv[1],language='en',beam_size=5,vad_filter=False,word_timestamps=True)
data=[{'start':round(z.start,2),'end':round(z.end,2),'text':z.text,
       'words':[{'start':round(w.start,2),'end':round(w.end,2),'word':w.word}
                for w in (z.words or [])]} for z in segments]
open(sys.argv[2],'w').write(json.dumps(data,indent=2))
print('QA_ASR_SEGMENTS='+json.dumps(data))
"""
        script = Path("qa_asr_once.py")
        script.write_text(pycode)
        run([str(venv/"bin/python"), str(script), str(source),
             "qa_asr_" + cid + ".json"])
        print("QA_ASR_ONLY_NO_PUBLICATION=true")
        return
    # QA-only licensed-stock photograph bridge; no posting or API publishing.
    if job.get("mode") == "photo_bridge":
        cid = job["clip_id"]
        need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{6,72}", cid)), "Invalid photo bridge id")
        srcs = job.get("photos") or {}
        need(1 <= len(srcs) <= 24, "Expected 1-24 photos")
        for key, url in srcs.items():
            need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{1,35}", key)), "Unsafe photo label")
            need(url.startswith("https://images.pexels.com/photos/"), "Only official Pexels CDN URL accepted")
            dest = Path("asset_" + cid + "_" + key + ".jpg")
            run(["curl", "-fL", "--retry", "2", "--connect-timeout", "30",
                 "--max-time", "120", "-A", "Mozilla/5.0", url, "-o", str(dest)])
            need(dest.stat().st_size > 10000, "Downloaded file too small")
            pmeta = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_name,width,height", "-of", "json", str(dest)
            ], text=True))
            pics = [p for p in pmeta.get("streams", []) if p.get("width")]
            need(pics and pics[0]["width"] >= 400 and pics[0]["height"] >= 300,
                 "Downloaded asset is not a usable photo")
            print("PHOTO_BRIDGE=" + key + " BYTES=" + str(dest.stat().st_size) +
                  " SHA256=" + digest(dest))
        print("PHOTO_BRIDGE_QA_HOLD_NO_PUBLICATION=true")
        return
    # One-off original-audio recovery into the existing GitHub Actions artifact store.
    # This mode cannot publish and does not touch the approved-source pipeline.
    if job.get("mode") == "audio_bridge":
        cid = job["clip_id"]
        need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{6,72}", cid)), "Invalid audio bridge id")
        audio_urls = job.get("audio_urls") or {"full": job["audio_url"]}
        need(1 <= len(audio_urls) <= 20, "Expected 1-20 named audio files")
        for part, url in audio_urls.items():
            need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{1,40}", part)), "Unsafe part name")
            need(url.startswith("https://"), "HTTPS audio URL required")
            media = Path("audio_" + cid + "_" + part + ".mp3")
            run(["curl", "-fL", "--retry", "2", "--connect-timeout", "30",
                 "--max-time", "180", url, "-o", str(media)])
            result = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_name,codec_type:format=duration", "-of", "json", str(media)
            ], text=True))
            need(any(s.get("codec_type") == "audio" for s in result.get("streams", [])),
                 "Recovered URL is not audio")
            need(0.3 <= float(result["format"]["duration"]) <= 120, "Unexpected audio duration")
            print("AUDIO_PART=" + part + " BYTES=" + str(media.stat().st_size) +
                  " SHA256=" + digest(media) + " DURATION=" + result["format"]["duration"])
        print("AUDIO_BRIDGE_QA_HOLD_NO_PUBLICATION=true")
        return
    cid = job["clip_id"]
    need(bool(re.fullmatch(r"[a-zA-Z0-9_-]{6,72}", cid)), "Invalid clip ID")
    platform = job["platform"]
    need(platform in CHANNELS, "Invalid platform")
    url = job["source_url"]
    need(url.startswith("https://"), "HTTPS direct video URL required")
    need("source_sha256" in job and re.fullmatch(r"[a-f0-9]{64}",job["source_sha256"]), "Source hash required")
    need(job["mode"] in ("approved_source", "caption_reframe"), "Invalid edit mode")
    approval = bool(job.get("publish_approved", False))
    tag = "clipnerve-" + cid
    media = Path("output_" + cid + ".mp4")
    source = Path("source_" + cid + ".mp4")
    # The exact source hash prevents Drive preview/login HTML or wrong downloads.
    run(["curl", "-fL", "--retry", "3", "--connect-timeout", "30",
         "--max-time", "360", url, "-o", str(source)])
    need(digest(source) == job["source_sha256"], "Source SHA256 mismatch")
    if "source_size" in job:
        need(source.stat().st_size == int(job["source_size"]), "Source size mismatch")
    if job["mode"] == "approved_source":
        run(["cp", str(source), str(media)])
    else:
        start = float(job["start_seconds"])
        length = float(job["duration_seconds"])
        need(0 <= start <= 3600 and 1.0 < length <= 180, "Invalid time window")
        ass_text = job["captions_ass"]
        need("[Events]" in ass_text and "[V4+ Styles]" in ass_text,
             "Full authored ASS captions required")
        Path("captions.ass").write_text(ass_text, encoding="utf-8")
        # Preserve the existing 9:16 visual canvas and draw only authored captions.
        run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(start), "-i", str(source), "-t", str(length),
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
                   "crop=1080:1920,ass=captions.ass",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
            "-movflags", "+faststart", str(media)])
    result = probe(media)
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(media),
         "-f", "null", "-"])
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-ss", "1", "-i", str(media), "-frames:v", "1",
         "qa_" + cid + ".jpg"])
    actual = digest(media)
    print("OUTPUT_SHA256=" + actual)
    print("OUTPUT_BYTES=" + str(media.stat().st_size))
    print("OUTPUT_DURATION=" + str(result["format"]["duration"]))
    print("RENDER_QA=CODEC_RESOLUTION_DECODE_PASS; VISUAL_AUDIO_SEMANTIC_UNVERIFIED")
    # Only an exact previously-reviewed output hash may be published.
    if not approval:
        print("QA_HOLD - video built for review; NO BUFFER SUBMISSION")
        return
    need(job.get("source_rights_confirmed") is True, "Rights gate unconfirmed")
    need(bool(job.get("source_rights_evidence")), "Rights evidence required")
    need(bool(job.get("visual_qa_evidence")), "Visual QA evidence required")
    need(bool(job.get("audio_qa_evidence")), "Audio QA evidence required")
    need(job.get("approved_sha256") == actual, "Final reviewed SHA256 mismatch")
    need(job["buffer_mode"] in ("shareNow", "addToQueue"), "Unapproved Buffer mode")
    need("title" in job and "caption" in job, "Missing publishing metadata")
    run(["gh", "release", "create", tag, str(media) + "#" + cid + ".mp4",
         "--title", "ClipNerve " + cid, "--notes",
         "QA approved, exact-SHA verified " + cid, "--latest=false"])
    public = "https://github.com/" + REPO + "/releases/download/" + tag + "/" + cid + ".mp4"
    print("PUBLIC_MEDIA_URL=" + public)
    gql_post(job, public)

if __name__ == "__main__":
    main(sys.argv[1])
