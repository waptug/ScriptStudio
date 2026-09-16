# Architecture

React/TypeScript talks to FastAPI through a same-origin Nginx proxy. SSE publishes
full project snapshots on changes and heartbeat comments otherwise. Only localhost
port 8088 is exposed. FastAPI and Celery share PostgreSQL plus persistent local media;
Redis carries wakeups, never authoritative state. Beat reconciles every three seconds.

## Boundaries

- `ScriptPlanner`: validated scenes/shots from paragraph-based local planning or a
  configured local Ollama model / operator-defined JSON gateway. Bracketed visual directions are not spoken.
- `NarrationService`: retains text/settings/alignment and derives word caption cues.
- `GenerationCoordinator`: durable submission/poll/download/validation state machine.
- `BudgetService`: reserves estimated USD under the project row lock, including queued,
  in-flight, uncertain, and potentially charged failed/canceled requests.
- `AssetRepository` / `LocalStorage`: bounded download/upload, full decode validation,
  ffprobe metadata, SHA-256, atomic promotion, thumbnail, and video proxy.
- `TimelineService`: optimistic revision checks under a PostgreSQL project row lock,
  immutable revisions, manual undo/redo history, and conservative automatic fill.
- `OpenShotVisualService`: normalized source clips and native libopenshot composition.
- `RenderService`: fixed snapshot, exact frame duration, 48 kHz audio mixing, sidechain
  ducking, fades, MP4 encoding, subtitle export, and native OpenShot project packaging.

## Timing and timeline specification

Version 1 uses integer frames and an explicit rational FPS numerator/denominator.
Seconds = frames × denominator / numerator. Source in/out uses the same project
frame domain. `source_out = source_in + duration`. Audio start converts once to a
48 kHz sample count; narration is never sped up. Speech scene duration is measured
with ffprobe and rounded upward once to project frames, padding the fractional final frame. Shot allocation partitions that
scene's integer duration using cumulative weights, so its shots exactly cover it.

Tracks: video, overlay, title, caption, narration, music, and sfx. Native visual layer
order is video < overlay < title < caption. Visuals fit within the project rectangle;
scale is 0–1, positions specify a 0–1 fraction of the free space. Titles use text
images; captions use bottom-centered images. Visual fades affect alpha. Audio fades
are linear. Video audio is intentionally excluded; use narration/music/sfx assets.
Overlapping audio is mixed, music is sidechain-ducked by the narration bus, and a
limiter protects the output. Coverage is explicit hold-last-frame or loop for video,
and silence padding or loop for audio. Transform/volume controls irrelevant to a
track are disabled. Cut and fade-in transitions are supported; no hidden effects.

Preview is a worker-rendered MP4 from the identical timeline specification, using
proxies and reduced output size. Rebuild after changes; revision labels prevent
confusing an old preview with a new edit. Browser playback/seeking uses that single
synchronized video/audio stream. Export snapshots timeline AND settings at request
time, regardless of subsequent edits.

## Assembly invariants

After all scene narrations are stored, one transaction creates the measured timeline
and video jobs. No video request can run before its placeholder exists. Completion
locates the original placeholder ID, rather than searching by time or sequence.
It fills only a surviving, unlocked, empty, non-selected placeholder. Moves/trims
are preserved. Deletions remain deleted. Duplicate events cannot create items.
Regeneration has a new job/asset ID and leaves the prior take intact. Explicit take
selection and undo/redo are user edits and create new immutable revisions.

## Job recovery

`queued → submitting → submitted → generating → downloading → validating → ready`.
Synchronous providers can bypass remote polling while still persisting stages.
Failed/canceled/unknown are explicit terminal states. Requests carry fingerprints,
provider IDs, settings, references, submission attempts, retries, costs, errors,
results, timestamps, and asset IDs. A stable job-based asset ID deduplicates ingestion.

Workers claim under the project lock and a lease. Claims become `submitting` in the
same transaction, so simultaneous queued work cannot bypass concurrency. Existing
remote jobs count as active while waiting for polls. Duplicate broker messages
cannot claim a live lease. A lost worker's lease expires after ten minutes; renders
refresh their lease as progress arrives. Expired live `submitting` jobs become
`submission_outcome_unknown`, without automatic resubmission. Mock work may safely
restart. Existing provider task IDs resume polling/download after restart.

HTTP 429 retries use bounded exponential backoff; status/download failures retain
the existing provider task. Five failures require explicit retry. Runway POST has
no undocumented idempotency header. Ambiguous outcomes retain their budget reservation;
users reconcile an existing task ID. Synchronous uncertain narration must be recovered
from provider history as an imported asset. No webhook listener is exposed for a
localhost-only installation: documented task polling plus reconciliation is used.
