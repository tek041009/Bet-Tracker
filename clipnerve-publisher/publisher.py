from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import requests
from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parent
TOKEN_STATE = ROOT / "token-state.enc"
STATUS_DIR = ROOT / "status"
STATUS_DIR.mkdir(parents=True, exist_ok=True)

API = "https://open.tiktokapis.com"
TOKEN_URL = f"{API}/v2/oauth/token/"
CREATOR_INFO_URL = f"{API}/v2/post/publish/creator_info/query/"
DIRECT_POST_URL = f"{API}/v2/post/publish/video/init/"
STATUS_URL = f"{API}/v2/post/publish/status/fetch/"

NON_RETRYABLE = {
    "spam_risk_too_many_posts",
    "spam_risk_user_banned_from_posting",
    "spam_risk_text",
    "spam_risk",
    "scope_not_authorized",
    "access_token_invalid",
}


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def derive_fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def load_token_state() -> dict[str, Any] | None:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY", "").strip()
    if not key:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is required")
    if not TOKEN_STATE.exists():
        return None
    blob = TOKEN_STATE.read_bytes()
    data = derive_fernet(key).decrypt(blob)
    return json.loads(data.decode("utf-8"))


def save_token_state(state: dict[str, Any]) -> None:
    key = os.environ["TOKEN_ENCRYPTION_KEY"].strip()
    blob = derive_fernet(key).encrypt(
        json.dumps(state, separators=(",", ":")).encode("utf-8")
    )
    TOKEN_STATE.write_bytes(blob)


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    payload = {
        "client_key": os.environ["TIKTOK_CLIENT_KEY"],
        "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }
    r = requests.post(
        TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"TikTok token refresh failed: {safe_json(data)}")
    now = int(time.time())
    state = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "open_id": data.get("open_id"),
        "scope": data.get("scope", ""),
        "token_type": data.get("token_type", "Bearer"),
        "access_expires_at": now + int(data.get("expires_in", 86400)),
        "refresh_expires_at": now + int(data.get("refresh_expires_in", 31536000)),
    }
    save_token_state(state)
    return state


def get_access_token() -> str:
    state = load_token_state()
    if state is None:
        initial = os.environ.get("TIKTOK_REFRESH_TOKEN", "").strip()
        if not initial:
            raise RuntimeError(
                "No encrypted token state exists and TIKTOK_REFRESH_TOKEN is missing"
            )
        state = refresh_tokens(initial)
    elif int(state.get("access_expires_at", 0)) <= int(time.time()) + 1800:
        state = refresh_tokens(state["refresh_token"])
    return state["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
    }


def safe_json(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False)
    for key in (
        os.environ.get("TIKTOK_CLIENT_SECRET", ""),
        os.environ.get("TIKTOK_REFRESH_TOKEN", ""),
        os.environ.get("TOKEN_ENCRYPTION_KEY", ""),
    ):
        if key:
            text = text.replace(key, "[REDACTED]")
    return text


def api_post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    r = requests.post(url, headers=auth_headers(token), json=payload, timeout=45)
    body: dict[str, Any]
    try:
        body = r.json()
    except Exception:
        body = {"error": {"code": f"http_{r.status_code}", "message": r.text[:1000]}}
    error = body.get("error") or {}
    code = error.get("code", "ok")
    if r.status_code >= 400 or code != "ok":
        exc = RuntimeError(
            f"TikTok API error http={r.status_code} code={code}: "
            f"{error.get('message', '')}"
        )
        setattr(exc, "tiktok_code", code)
        raise exc
    return body


def query_creator(token: str) -> dict[str, Any]:
    return api_post(CREATOR_INFO_URL, token, {}).get("data", {})


def validate_post_options(job: dict[str, Any], creator: dict[str, Any]) -> dict[str, Any]:
    post = dict(job.get("post") or {})
    allowed_privacy = creator.get("privacy_level_options") or []
    requested = post.get("privacy_level", "PUBLIC_TO_EVERYONE")
    if allowed_privacy and requested not in allowed_privacy:
        raise RuntimeError(
            f"Requested privacy_level={requested} not allowed; "
            f"TikTok returned {allowed_privacy}"
        )

    if creator.get("comment_disabled"):
        post["disable_comment"] = True
    if creator.get("duet_disabled"):
        post["disable_duet"] = True
    if creator.get("stitch_disabled"):
        post["disable_stitch"] = True

    post.setdefault("title", "")
    post.setdefault("disable_comment", False)
    post.setdefault("disable_duet", False)
    post.setdefault("disable_stitch", False)
    post.setdefault("video_cover_timestamp_ms", 1000)
    post["privacy_level"] = requested
    return post


def ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def ass_escape(text: str) -> str:
    return (
        str(text)
        .replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def write_ass(job: dict[str, Any], duration: float, path: Path) -> bool:
    hook = str(job.get("hook") or "").strip()
    captions = job.get("captions") or []
    if not hook and not captions:
        return False

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        "Style: Hook,Arial,66,&H00FFFFFF,&H000000FF,&H00000000,&H70000000,-1,0,0,0,100,100,0,0,1,4,0,8,60,60,125,1",
        "Style: Caption,Arial,62,&H00FFFFFF,&H000000FF,&H00000000,&H70000000,-1,0,0,0,100,100,0,0,1,4,0,2,70,70,245,1",
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
    ]
    if hook:
        hook_end = min(max(duration, 0.1), 3.6)
        lines.append(
            f"Dialogue: 0,{ass_time(0)},{ass_time(hook_end)},Hook,,0,0,0,,{ass_escape(hook)}"
        )
    for item in captions:
        start = float(item["start"])
        end = float(item["end"])
        text = ass_escape(item["text"])
        if end > start and start < duration:
            lines.append(
                f"Dialogue: 0,{ass_time(start)},{ass_time(min(end, duration))},Caption,,0,0,0,,{text}"
            )
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def download_source(job: dict[str, Any], work: Path) -> Path:
    if job.get("media_url"):
        target = work / "input.mp4"
        with requests.get(job["media_url"], stream=True, timeout=120) as r:
            r.raise_for_status()
            with target.open("wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
        return target

    source_url = job.get("source_url")
    if not source_url:
        raise RuntimeError("Job needs either media_url or source_url")

    template = str(work / "source.%(ext)s")
    run(
        [
            sys.executable,
            "-m",
            "yt_dlp",
            "--no-playlist",
            "--merge-output-format",
            "mp4",
            "-f",
            "bv*[height<=1080]+ba/b[height<=1080]/b",
            "-o",
            template,
            source_url,
        ]
    )
    candidates = sorted(work.glob("source.*"))
    if not candidates:
        raise RuntimeError("yt-dlp completed without producing a source file")
    return candidates[0]


def render(job: dict[str, Any], source: Path, work: Path) -> Path:
    clip = job.get("clip") or {}
    if not clip and job.get("media_url") and not job.get("force_render"):
        return source

    start = float(clip.get("start", 0))
    end = float(clip.get("end", 0))
    if end <= start:
        raise RuntimeError("clip.end must be greater than clip.start")
    duration = end - start

    ass = work / "captions.ass"
    has_ass = write_ass(job, duration, ass)
    output = work / "final.mp4"

    filter_graph = (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=28,eq=brightness=-0.18[bg2];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg2];"
        "[bg2][fg2]overlay=(W-w)/2:(H-h)/2[base]"
    )
    if has_ass:
        ass_path = str(ass).replace("\\", "/").replace(":", r"\:")
        filter_graph += f";[base]subtitles='{ass_path}'[vout]"
        map_video = "[vout]"
    else:
        map_video = "[base]"

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-t",
        str(duration),
        "-i",
        str(source),
        "-filter_complex",
        filter_graph,
        "-map",
        map_video,
        "-map",
        "0:a?",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-af",
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-movflags",
        "+faststart",
        output.as_posix(),
    ]
    run(cmd)
    return output


def probe_video(path: Path) -> None:
    run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,pix_fmt",
            "-of",
            "json",
            str(path),
        ]
    )


def chunk_plan(size: int) -> tuple[int, int]:
    if size <= 64 * 1024 * 1024:
        return size, 1
    chunk = 32 * 1024 * 1024
    count = max(1, size // chunk)
    return chunk, count


def init_direct_post(
    token: str, post: dict[str, Any], video_path: Path
) -> tuple[str, str]:
    size = video_path.stat().st_size
    chunk_size, total_chunks = chunk_plan(size)
    payload = {
        "post_info": post,
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
    }
    body = api_post(DIRECT_POST_URL, token, payload)
    data = body.get("data") or {}
    publish_id = data.get("publish_id")
    upload_url = data.get("upload_url")
    if not publish_id or not upload_url:
        raise RuntimeError(f"TikTok init returned incomplete data: {safe_json(body)}")
    return publish_id, upload_url


def upload_video(upload_url: str, path: Path) -> None:
    total = path.stat().st_size
    chunk_size, total_chunks = chunk_plan(total)
    start = 0
    with path.open("rb") as f:
        for idx in range(total_chunks):
            if idx == total_chunks - 1:
                body = f.read()
            else:
                body = f.read(chunk_size)
            if not body:
                break
            end = start + len(body) - 1
            headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(len(body)),
                "Content-Range": f"bytes {start}-{end}/{total}",
            }
            r = requests.put(upload_url, data=body, headers=headers, timeout=180)
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(
                    f"TikTok upload failed http={r.status_code}: {r.text[:1000]}"
                )
            start = end + 1
    if start != total:
        raise RuntimeError(f"Upload incomplete: sent {start} of {total} bytes")


def poll_status(token: str, publish_id: str, timeout_sec: int = 900) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {}
    while time.time() < deadline:
        body = api_post(STATUS_URL, token, {"publish_id": publish_id})
        data = body.get("data") or {}
        last = data
        status = data.get("status")
        if status == "PUBLISH_COMPLETE":
            return data
        if status == "FAILED":
            reason = data.get("fail_reason", "unknown")
            exc = RuntimeError(f"TikTok processing failed: {reason}")
            setattr(exc, "tiktok_code", reason)
            raise exc
        time.sleep(15)
    return {"status": "POLL_TIMEOUT", "last": last}


def status_path(job_id: str) -> Path:
    safe = "".join(c for c in job_id if c.isalnum() or c in ("-", "_"))
    return STATUS_DIR / f"{safe}.json"


def write_status(job_id: str, payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["job_id"] = job_id
    payload["updated_at"] = int(time.time())
    status_path(job_id).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: publisher.py path/to/job.json")

    job_path = Path(sys.argv[1])
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job_id = str(job.get("id") or job_path.stem)

    existing = status_path(job_id)
    if existing.exists():
        prior = json.loads(existing.read_text(encoding="utf-8"))
        if prior.get("state") == "published":
            print(f"{job_id}: already published; refusing duplicate")
            return 0

    write_status(job_id, {"state": "starting", "job_file": job_path.as_posix()})

    try:
        token = get_access_token()
        creator = query_creator(token)
        post = validate_post_options(job, creator)

        with tempfile.TemporaryDirectory(prefix="clipnerve-") as tmp:
            work = Path(tmp)
            source = download_source(job, work)
            final = render(job, source, work)
            probe_video(final)

            write_status(job_id, {"state": "uploading"})
            publish_id, upload_url = init_direct_post(token, post, final)
            upload_video(upload_url, final)

            write_status(
                job_id,
                {"state": "processing", "publish_id": publish_id},
            )
            result = poll_status(token, publish_id)

        if result.get("status") == "PUBLISH_COMPLETE":
            write_status(
                job_id,
                {
                    "state": "published",
                    "publish_id": publish_id,
                    "tiktok_status": result.get("status"),
                    "post_ids": result.get("publicaly_available_post_id") or [],
                },
            )
            print(f"{job_id}: published")
            return 0

        write_status(
            job_id,
            {
                "state": "processing_timeout",
                "publish_id": publish_id,
                "tiktok_status": result,
            },
        )
        print(f"{job_id}: upload accepted; status polling timed out")
        return 0

    except Exception as exc:
        code = getattr(exc, "tiktok_code", None)
        state = "blocked" if code in NON_RETRYABLE else "failed"
        write_status(
            job_id,
            {
                "state": state,
                "error_code": code,
                "error": str(exc),
            },
        )
        print(f"{job_id}: {state}: {exc}", file=sys.stderr)
        return 2 if state == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
