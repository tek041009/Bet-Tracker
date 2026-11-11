# Panna approved missing-data runtime guard — 11 November 2026

**Applies to:** Bet Picker and Sports Simulation Lab; original approved 27 competitions; V14 Panna source snapshot. Owner explicitly approved continued work despite expected gaps in low-profile early FA Cup/qualifiers and UEFA qualifiers. **Missing data must never be treated as zero.**

## Source-of-truth and integration contract

`panna_coverage_gate.py` is a pure Python / SQLite read-only guard. It requires the original V14 SQLite (the Drive verified master); it neither edits that DB nor loosens the independent V14 raw-source, extra-time, and penalty-shootout rules. To use it in a consumer, import `CoverageGate` and call `check(match_id, layer, metric)` **before querying a metric** or interpreting a missing value.

`layer` is `player` (native per-player boxscore) or `events` (detailed event feed). For player shot/tackle/foul/dribble/minutes metrics, `metric` must be supplied, and the named metric's quality plus minutes quality must pass. The overall match quality may be BLOCK because another, unrelated metric fails; use the named metric *only* when all its own gates pass and there is no unsafe extra time or missing substitute scorer. For general, unqualified native player aggregates, the overall V14 PASS gate remains mandatory.

When the detailed feed is missing but the native player boxscore exists, a validated player metric can still be used. Missing detailed events never imply zero events, shots or fouls.

**Source gap return actions** (all missing rows have `usable_for_metric=false`):

- `EXPECTED_SOURCE_GAP`: previously observed low availability in low-profile early cup or qualifying fixture. Record and skip *the unavailable layer only*; do not block the whole process.
- `REVIEW_MISSING`: unclear stage / professional involvement / insufficient baseline. Add QA work item; skip that layer without fabricating values. Do not silently approve.
- `INVESTIGATE_MISSING`: important professional match, main stage, or normally high-availability source absent. Escalate QA, still do not invent or count anything.
- `UNKNOWN_FIXTURE`: match not in verified fixture registry; halt market interpretation for that match, investigate identity/data join.
- `USE_SOURCE`: source layer exists, **not a free pass**. Use `usable_for_metric`, and for event-derived work only use the regulation-period V14 views, never raw 120-minute/shootout events.

For every estimate/hit-rate, preserve sample size and excluded counts. `CoverageGate.sample(observations, layer, min_eligible, metric)` returns `INSUFFICIENT_DATA` rather than a fake percentage when there aren't enough verified observations. Caller must provide genuine player/team appearances, not assume a player appeared in all team games. Actual numeric zero is valid; null, NaN, infinity, negatives, booleans, malformed values and duplicate match IDs are excluded. **No betting recommendation is enabled.**

## Baseline classification

Historical comparator is 2025/26; this season is 2026/27. Date windows approximate early FA Cup and UEFA qualifying stages. This heuristic is NOT a certified official round field. A missing player boxscore cannot be waived on the basis of an event feed's historically poor coverage: each layer receives a separate decision. Early-stage automatic exceptions require at least 20 historical fixtures and less than 50% last-season coverage of the *specific missing layer*, plus no top-professional club or professional-pair override. October FA Cup is intentionally a REVIEW stage because its round mix varies by year.

Professional-team presence is inferred from this dataset's EPL / Championship / League Cup participants. This is a proxy, not complete tier classification. If critical professional club coverage may be missed by the proxy, mark for human review; never assert that nonappearance in these datasets proves an amateur side.

## Real V14 2026/27 runtime policy audit

| Layer | Source present | Expected source gaps | Review | Investigate |
|---|---:|---:|---:|---:|
| Player-match statistics | 1,640 | 655 | 45 | 0 |
| Detailed event feed | 1,307 | 916 | 116 | 1 |

Counts are per **fixture per source layer**, not unique matches: a fixture may lack both and appears in both categories. Every one of the 1,733 missing-layer observations has a classification and a traceable fixture/previous-season explanation. These counts apply only to the snapshot's `season=2026-2027`, not international season labels or later live fixtures.

**High-priority exception found:** 7 Nov 2026 Oxford United v Stevenage, native player boxscore present, detailed events missing: `INVESTIGATE_MISSING`, not an approved exception.

**Representative test:** Fleetwood Town v Rochdale, 7 Nov 2026, event feed missing. Its Panna shot, foul and minutes quality each PASS, tackles/dribbles quality BLOCK. The runtime guard can accept verified *shots/fouls* as metric-only boxscore evidence while excluding tackles and event-derived features. It never changes the original V14 `BLOCK` status or misrepresents the whole match as fully validated.

## Deploy and verification

```bash
python -m unittest -v test_panna_coverage_gate.py
python panna_coverage_gate.py --database /path/to/PANNA_V14_APPROVED_27_SCOPE_SQLITE.sqlite --audit --output coverage_audit.json
python panna_coverage_gate.py --database /path/to/PANNA_V14_APPROVED_27_SCOPE_SQLITE.sqlite --match-id <ACTUAL_PANNA_ID> --layer player --metric shots
```

The implementation and its tests are stored in the Panna data-layer source branch. **The guard must still be explicitly imported and invoked by each live Bet Picker / Sports Simulation Lab consumer before it can prevent application-level crashes.** Neither production application is claimed patched until its own integration tests pass. Do not repackage the 5.7 GB V14 source snapshot merely to add this policy.
