# ClipNerve Publisher

This folder is the autonomous publishing bridge for ClipNerve.

## Runtime

The core path is:

1. A ChatGPT scheduled ClipNerve run selects/creates a clip job.
2. The run commits a JSON job into `clipnerve-publisher/jobs/`.
3. That commit automatically triggers `.github/workflows/clipnerve-publish.yml`.
4. GitHub Actions downloads the original source, renders the specified vertical clip when needed, refreshes the TikTok user token, uploads the MP4 with TikTok's official Content Posting API, polls the result, and writes a durable status file.
5. The Action commits only encrypted token state plus non-secret publish status back into the repository.
6. Future scheduled runs can read `clipnerve-publisher/status/` to see exact publish results.

No PC is required in the publishing path. Metricool is not required for publishing.

## One-time GitHub Actions secrets

These secrets must be configured once in the repository:

- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_REFRESH_TOKEN` — bootstrap refresh token from the ClipNerve TikTok OAuth grant
- `TOKEN_ENCRYPTION_KEY` — any strong random secret; used to derive the encryption key for the rotating TikTok token state

After the first successful run, current TikTok token state is stored only as encrypted ciphertext in `token-state.enc`. TikTok may rotate refresh tokens; the publisher replaces the encrypted state automatically.

Never commit raw TikTok credentials or tokens.

## TikTok app requirement

The TikTok developer app must have the required Login Kit / Content Posting access and `video.publish` approval for public Direct Post. TikTok's own anti-spam and posting limits remain authoritative and are not bypassed.

## Job format

See `examples/job.example.json`.

The preferred handoff does not require hosting the finished MP4 elsewhere. The job can contain an original `source_url`, clip start/end, hook and timed captions. GitHub Actions downloads and renders the final MP4 inside the runner, then performs a TikTok `FILE_UPLOAD`.

A job may alternatively provide `media_url` when a finished MP4 already has a reliable direct URL.

## Idempotency

Each job has a unique `id`. Once its status is `published`, rerunning the same job refuses to publish a duplicate.

## Statuses

Status files are written to `clipnerve-publisher/status/<job-id>.json`.

Important states include:

- `starting`
- `uploading`
- `processing`
- `published`
- `processing_timeout`
- `blocked`
- `failed`

TikTok spam/risk responses are recorded as blocked rather than hammered with automatic retries.
