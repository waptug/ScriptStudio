# ScriptStudio implementation plan

## Docker projects copied to D: (2026-09-19)

- [x] Use the current Docker projects as the migration source, per user direction;
  leave the unresponsive E: originals untouched.
- [x] Take a consistent PostgreSQL snapshot with project tables locked against
  writes; confirm no active source jobs and validate original asset checksums.
- [x] Back up the destination database before importing. Preserve all existing
  10 D: projects and local-model/credential settings; do not replace AppSettings.
- [x] Import 65 projects, 276 revisions, 184 assets, and 220 terminal jobs in one
  transaction, preserving IDs, timelines, selected takes, undo/redo, and history.
- [x] Verify all 2,902 copied files, all 65 project documents through the native
  API, all 184 original asset endpoints, and an imported preview download hash.
- [x] Verify the 75-project dashboard and playback of **Lovely Day** in native
  Edge. Rebuild its preview with Windows libopenshot; timeline/revision unchanged.

Backups and verification reports are under
`D:\ScriptStudio\ScriptStudioNative\migrations\docker-20260919T131116Z`.
`docker-projects.zip` is the source snapshot; `native-before-import.dump` is the
pre-import destination database. Source archive SHA-256:
`2b987d2dbb2c4a5d65eaac73ca66def42b0a2944447f918e922bd93543a31dd5`.
The Docker installation remains unchanged and running. The existing
**ScriptStudio Local Models** desktop shortcut opens the combined D: workspace.
No paid generation or GPU-model inference was needed for this migration.

## Local media models on D: (in progress)

- [x] Confirm Windows RTX 3060 12 GB and E: free-space report (about 2.8 TiB).
- [x] Add native Windows dependency resolution and pinned-wheel extraction support.
- [x] Verify D: has about 705 GiB free and passes a native Windows write test.
- [x] Recover the exact native EXE to D: and verify/extract its embedded package.
- [x] Use the current Docker projects on D: instead of waiting for E: recovery.
  Recovery of any E:-only material is deferred; originals remain untouched.
- [x] Install Kokoro, Wan, and ACE-Step alongside the native app on D:.
- [x] Verify actual narration, video, and music generation on Windows.
- [ ] Install and verify Stable Audio sound effects after upstream authorization.
- [x] Verify local writing/planning, UI workflow, preview/export, and desktop launch.
- [x] Create a separate D: local-model workspace and desktop shortcut.
- [x] User confirmed Stable Audio upstream access approval.
- [ ] Save an authorized Hugging Face token through Admin, then finish Stable Audio installation.

Installation is not complete. Two native resolver attempts failed with Windows
error 21 (device not ready) creating
`E:\ScriptStudio\ScriptStudioNative\model-build`. Windows confirms the existing
app folder is a regular directory, not a junction. Kokoro, Wan, and ACE-Step now have pinned native Windows manifests. Kokoro
installed and generated 7.325 seconds of real narration through the native app
on D:. ACE-Step installed and generated 13.2 seconds of real music through the
native job pipeline (583 seconds elapsed under competing Minecraft/Ollama GPU
load). Wan has installed and passed its native runtime/CUDA probe; actual
video generation passed: 81 H.264 frames at 832 × 480 / 16 fps (5.0625 seconds).
The first run took 2362.66 seconds including slow paging/model loading; its
30 diffusion steps took 19 minutes 22 seconds. A decoded frame was visually checked. Local Ollama writing and structured
planning both passed with gemma3:4b in the separate validation workspace.
The backend suite passed 59 tests; PostgreSQL concurrency checks, frontend build,
and all 10 browser tests against the Docker app passed (two Admin selectors were
updated for the model panels). Native Admin readiness and a rendered preview with real Kokoro narration
were verified in Edge, including advancing video playback. Sound effects remain
unverified pending the protected token and installation. Real Wan/Kokoro final export passed through libopenshot and downloaded through
the app as a 582,443-byte MP4 (SHA-256
`35d36fe43f1f901fb8d72673eccfc9c2495d30ec8082fa2dc6598a95304b8454`). ACE-Step checkpoint code pinning, strict offline initialization, and additional
CPU offload passed a second real generation: a 10-second sample was trimmed to
4.75 seconds at unchanged tempo, with peak CUDA allocation 4.52 GiB. Its pinned
checkpoint code hashes remained unchanged afterward. Wan's runtime now includes
ftfy/imageio and its additional wheels match a native Windows dependency report.
Stable Audio public runtime resolution succeeded; the user has approved access,
but the protected Admin token is still not configured, so installation remains pending.
The launcher now supports a separate portable `--workspace local-models`; native
extraction, archive-safety, free-space, and workspace-path checks passed on D:.
Release source `953ad85` is packaged at
`D:\ScriptStudio\ScriptStudio-Local-Models.exe` (SHA-256
`b9386cee473e05e04acab6ead027753a7d94d429bd4fd1a98a3915da4ac6b323`),
with verified extracted package `5741f0b16a3970ac`. The desktop shortcut
**ScriptStudio Local Models** starts `--workspace local-models --start`.
The stopped validation database/media moved to `workspace-local-models`; all
8 projects and all 3 ready model states survived. Shortcut launch and a second
clean restart passed, with healthy services at `http://127.0.0.1:50757`, paid
permissions off, and visible launcher/editor windows. Packaged Edge checks
confirmed all 3 Ready panels, Stable Audio unavailable, and advancing playback
of a real Wan/Kokoro preview without page errors. Fresh Edge profile startup
stalled on this host; reusing the previously verified isolated profile resolved
visible startup, with both original profiles preserved. D: has about 646.7 GiB
free after installation. The original Docker desktop shortcut is unchanged.
The user subsequently selected D:. Its native application is verified at
`D:\ScriptStudio\ScriptStudio-Native-Windows-x64.exe`, recovered from the local
backup whose SHA-256 matches E:'s recorded application checksum. Package
`c59cb3999706cb58` successfully verified and extracted there. E: reads stalled
during project-data migration, so the source remains preserved and the desktop
original shortcut remains unchanged; the new local-model shortcut uses its own workspace. The first bulk-copy attempt left a locked,
unverified `D:\ScriptStudio\ScriptStudio.exe`; do not use that partial file.

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
