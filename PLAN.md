# ScriptStudio implementation plan

- [x] 1. Foundation: typed project/timeline models, PostgreSQL migrations, storage, Compose.
- [x] 2. Runnable mock production: planning, measured speech, shots, music, MP4.
- [x] 3. Durable orchestration: progressive assembly, budgets, recovery, takes.
- [x] 4. Editor: dashboard, storyboard, timeline operations, inspector, preview/export.
- [x] 5. Documented live adapters and configuration; no paid calls during development.
- [x] 6. Acceptance tests, browser smoke, deployment verification, documentation.

Completed locally: 27 backend tests, Chromium end-to-end workflow, PostgreSQL race
checks, actual worker/Redis restart recovery, 55.125-second sample preview/final,
and actual OpenShot 2.6.1 desktop bundle loading. See `docs/verification.md`.
Paid provider validation requires the documented external setup. Local script writing
has since been verified live, as recorded below.

## Prompt-to-script and Admin follow-up

- [x] Reviewable prompt-to-script workflow alongside manual writing.
- [x] Separate workflow model settings and installed local-model discovery.
- [x] Encrypted, write-only Runway/ElevenLabs credentials with replace/clear controls.
- [x] Runtime settings shared by API/workers with captured job models preserved.
- [x] Complete live local-inference check and browser verification; deploy locally.

## Paid generation controls

- [x] Persist master and text/video/audio/speech/music permissions in Admin.
- [x] Enforce permissions in adapters, queueing, and new worker submissions.
- [x] Preserve monitoring/retrieval of submitted tasks and existing budget checks.
- [x] Verify backend permission and recovery behavior (43 tests passed).
- [x] Verify browser controls and finish local deployment (3 Chromium tests passed;
  rebuilt Compose stack verified at localhost:8088 with all paid permissions off).

## Export download names

- [x] Use a safe project name and UTC render creation timestamp for MP4, OpenShot
  ZIP, SRT, and WebVTT downloads; capture names for new renders.
- [x] Verify all four download filenames in Chromium and deploy locally;
  frontend build, backend coverage, PostgreSQL checks, and 3 browser tests passed.

## About & attribution

- [x] Add About access from dashboard/editor, foundation credits, project license,
  searchable dependency inventory, and collected license notices.
- [x] Generate inventory from npm lockfile, installed Python metadata, and running
  Debian/Alpine package records; distinguish Redis 7.4 source-available licensing.
- [x] Verify browser navigation, notices, downloads, mobile layout, and deploy
  locally (44 backend tests and 4 Chromium tests passed).

## Decisions

Python/FastAPI services and Celery workers use PostgreSQL as authority. Redis only
transports work. Every edit and automatic placement acquires the project row lock.
Revisions are immutable; renders snapshot a revision. Preview uses the same renderer
at reduced resolution, ensuring timing/effect parity. Mock speech uses local eSpeak;
mock imagery is visibly synthetic FFmpeg footage, and music is synthesized locally.
Paid requests require both server authorization and a project spending limit.
Unknown submission outcomes remain reserved and require reconciliation.

## OpenShot integration (user direction)

Reuse libopenshot for visual composition, clip keyframes, and native project
serialization. Run its Debian Python bindings in a separate process to isolate
native crashes and Python ABI differences. FFmpeg normalizes source coverage and
mixes audio. Export a portable .osp handoff with editable visual clips, exact mixed
audio, original sources, subtitles, and ScriptStudio's revision snapshot.
