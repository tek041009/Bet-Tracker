# ClipNerve — Football IQ / Offside Rebound (V1)

Status: PRODUCTION BRIEF ONLY. Not rendered, QA approved, queued or published.
Format: original rights-clear animated football-rules quiz; 1080x1920 H.264/AAC; target 18.5s.

## Editorial sequence
00:00–00:02.3 Hook: THE OFFSIDE REBOUND TRAP.
00:02.3–00:04.6: A striker is in an offside position when a teammate shoots.
00:04.6–00:06.4: Goalkeeper makes a deliberate save.
00:06.4–00:08.4: The ball rebounds to that striker, who scores.
00:08.4–00:11.3: GOAL OR OFFSIDE? Three timed 650 Hz ticks, 3/2/1.
00:11.3–00:15.6: OFFSIDE. A goalkeeper's deliberate save does not reset offside.
00:15.6–00:18.5: DID YOU GET IT RIGHT? Follow for more Football IQ.

## Visual treatment
Deep navy background, pitch-green 9:16 diagram card, mint pitch markings, gold offside line. Distinctly labelled shooter, offside striker, last defender and goalkeeper. Readable 1–2-line centered typography with >110px side margins. No third-party video, audio, images or copyrighted football footage.

## Factual verification
IFAB Law 11 (2026): https://www.theifab.com/laws/latest/offside/ — an offside-position attacker who plays a ball rebounding from an opponent's deliberate save gains an advantage and is penalised.

## Reproducible render plan
Use the already approved GitHub Actions ubuntu-latest runner and FFmpeg only. Generate pitch/card graphics with FFmpeg drawbox; render precisely timed ASS captions; synthesize four short non-copyright audio tones via FFmpeg sine/adelay/amix; export yuv420p H.264/AAC +faststart. Decode entire MP4; ffprobe streams; inspect frames at 1, 3, 5, 7, 9, 12 and 16 seconds and verify actual audio/sync. Release MP4 + contact sheet + provenance via gh release create. Keep QA HOLD until reviewed; then use GitHub Release direct MP4 to Buffer separately per platform with verified receipts. Unique content key: football-iq-offside-v1-20261008. Do not republish an existing post.
