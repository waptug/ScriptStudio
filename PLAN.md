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

## Matching logo assets

- [x] Create a path-based SVG and matching multi-resolution ICO, use the mark in
  all application headers and browser favicons, and add About-page downloads.
- [x] Verify SVG rendering, ICO frames, MIME types, and downloads; deploy locally.

## Interface themes

- [x] Add keyboard-accessible dark/light toggles to every page header, a complete
  light palette, persistent browser selection, and synchronization across tabs.
- [x] Verify theme interactions, readability, and local deployment, including
  reloads, unsaved input, cross-tab updates, keyboard use, and blocked storage.

## Replication goal

- [x] Write a self-contained Codex `/goal` specification covering the application,
  architecture, safeguards, branding, themes, attribution, and acceptance checks.
- [x] Add About-page reading, clipboard copy, manual selection, and text download
  from one canonical public text file.
- [x] Verify copy/download parity and clipboard denial behavior; deploy locally.

## Windows offline executable

- [x] Build a Windows x64 launcher and single-file offline package containing
  application images, matching source, icon, and license notices.
- [x] Keep package services/data isolated from the development installation;
  document the required Linux Docker engine and Windows framework runtime.
- [x] Verify Windows extraction plus checksum, traversal, and missing-file rejection.
- [x] Verify real Windows EXE startup using Docker in WSL, packaged video workflow,
  native launcher rendering, and stop/restart persistence; build the release EXE.
  Docker Desktop and a native Docker-free port are not claimed as verified.

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

## Native standalone Windows follow-up

- [x] Bundle native PostgreSQL, Python API, OpenShot subprocess, FFmpeg, and speech.
- [x] Replace Windows Celery/Redis with bounded PostgreSQL polling through the same coordinator.
- [x] Add Windows credential-file locking and configurable media process boundaries.
- [x] Create branded self-extracting launcher with per-user data, loopback binding, graceful shutdown and Windows process containment.
- [x] Native backend acceptance: 45 tests passed, real media and portable OpenShot exports; PostgreSQL concurrency passed.
- [x] Packaged Windows browser: 8 passed; restart preserved 9 projects; native extraction safety and launcher checks passed.

No paid provider calls are part of native acceptance. Clean Windows machine and
complete third-party corresponding-source redistribution audits are not claimed.

## Host Ollama discovery

- [x] Detect local Ollama with private-address validation and model-list probes.
- [x] Atomically populate an empty URL while preserving manual configuration.
- [x] Show install/start, retry, and no-local-model guidance on dashboard and Admin.
- [x] Backend discovery and regression tests: 51 passed; PostgreSQL concurrency passed.
- [x] 10 browser tests and 50 native backend tests passed. Real Windows discovery found IPv6 loopback and persisted its URL.

## Script writer activity

- [x] Show pending requests with a spinner, indeterminate bar, and elapsed time.
- [x] Report completion and errors while preserving manual text and prior drafts.
- [x] Respect reduced motion and announce status without announcing each timer tick.

## Portable native storage

- [x] Resolve storage from the EXE folder; isolate child temporary/cache paths.
- [x] Check expanded package size plus 2 GiB working reserve on the destination volume.
- [x] Extract directly from the embedded ZIP; report insufficient space and close gracefully.
- [x] Keep the browser profile/download defaults portable; identify legacy project data.
- [x] Validate native extraction, low-space refusal, and Windows app workflows (51 backend / 10 browser tests).
