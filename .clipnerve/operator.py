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
