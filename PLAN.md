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
Paid provider and live local-LLM validation require the documented external setup.

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
