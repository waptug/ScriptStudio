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

## Local media models on D:

- [x] Confirm Windows RTX 3060 12 GB and E: free-space report (about 2.8 TiB).
- [x] Add native Windows dependency resolution and pinned-wheel extraction support.
- [x] Verify D: has about 705 GiB free and passes a native Windows write test.
- [x] Recover the exact native EXE to D: and verify/extract its embedded package.
- [x] Use the current Docker projects on D: instead of waiting for E: recovery.
  Recovery of any E:-only material is deferred; originals remain untouched.
- [x] Install Kokoro, Wan, and ACE-Step alongside the native app on D:.
- [x] Verify actual narration, video, and music generation on Windows.
- [x] Install and verify Stable Audio sound effects after upstream authorization.
- [x] Verify local writing/planning, UI workflow, preview/export, and desktop launch.
- [x] Create a separate D: local-model workspace and desktop shortcut.
- [x] User confirmed Stable Audio upstream access approval.
- [x] Save an authorized Hugging Face token through Admin and confirm gated access.
- [x] Finish Stable Audio installation and real sound-effect validation.

All four models have now produced real media on D:. Two initial native resolver attempts failed with Windows
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
were verified in Edge, including advancing video playback. Stable Audio sound effects are now verified with the authorized protected token. Real Wan/Kokoro final export passed through libopenshot and downloaded through
the app as a 582,443-byte MP4 (SHA-256
`35d36fe43f1f901fb8d72673eccfc9c2495d30ec8082fa2dc6598a95304b8454`). ACE-Step checkpoint code pinning, strict offline initialization, and additional
CPU offload passed a second real generation: a 10-second sample was trimmed to
4.75 seconds at unchanged tempo, with peak CUDA allocation 4.52 GiB. Its pinned
checkpoint code hashes remained unchanged afterward. Wan's runtime now includes
ftfy/imageio and its additional wheels match a native Windows dependency report.
Stable Audio public runtime resolution succeeded; the user has approved access,
and the protected Admin token now passes account and gated-model authorization.
The installer now pins the separate T5-base encoder/tokenizer and loads it from
a local path under the offline inference environment. Stable Audio installation
and real generation validation passed. Its 70-artifact manifest includes the
Python 3.10 runtime, missing upstream Lightning/torchmetrics dependencies, and
separate T5 encoder/tokenizer. The deeper readiness probe imports the actual
diffusion implementation, not only the package namespace.

On 2026-09-19, project `9435f08e-64c2-46c9-82d8-53690fb309c2` generated
asset/job `fb144a72-54a6-4bfa-b2bb-391686d36feb`: five seconds of real 44.1 kHz
stereo sound, 54.62 seconds elapsed, peak CUDA allocation 2,808,555,008 bytes.
The surviving SFX placeholder received the selected take at frame 0 for 120
frames at 24 fps. Original audio measured -19.8 dB mean volume. Native OpenShot
export `0ce3de11-dd26-47b7-a4cc-84fdabbd3d89` produced a 94,687-byte MP4 with
non-silent audio. The separately authorized Minecraft companion pause was
reversed after GPU validation; the companion is running again. No paid calls.
Current source backend checks: 59 passed; PostgreSQL concurrency and frontend
build passed. Browser suite: nine passed initially; the workflow exceeded its
90-second production wait under installation load, then passed on targeted rerun.
Native Chrome confirmed four Ready model panels, an enabled sound-effect
generator, and advancing five-second preview playback with no page errors.
The launcher now supports a separate portable `--workspace local-models`; native
extraction, archive-safety, free-space, and workspace-path checks passed on D:.
The initial three-model release, source `953ad85`, was packaged at
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
The final four-model desktop release uses source `756f8a8` and package
`369a5d3b8fa6dea5`, installed at `D:\ScriptStudio\ScriptStudio-Local-Models.exe`
(SHA-256 `47dac212eb07c8b4722a2f98cad9e8d81cb7d7385d22e79dfe75490f0b89a2f4`).
Extraction and source/manifest comparison passed. Desktop shortcut restart
preserved all 77 then-current project documents, the protected credential, and
four Ready model states; paid generation remained disabled. Native Chrome
rechecked all four panels and advancing SFX preview playback after replacement,
with no page errors. The launcher and editor windows are visible. The previous
EXE is retained under `ScriptStudioNative\release-backups`, and its original
cached package was restored for rollback. Closing the owned editor window
released its live-update connection so the old service could drain cleanly.

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

## Park-bench local workflow test — 2026-09-19

User prompt: “A man and a women sitting on a park bench in summer time talking
about the weather”. Project: **Summer Park Bench — Local System Test**
(`8baa8ef5-cd47-4dbc-9302-df3df193e2f7`). Gemma3:4b generated a draft; review
kept a short weather exchange and one continuous shot. Ollama planning twice
failed the exact-narration preservation check, so deterministic planning was
used and the storyboard reviewed before production. This is a fallback success,
not a passing Ollama planner test for this script.

All four native local media jobs completed without retries: Kokoro narration
70.45 seconds, Stable Audio ambience 81.34 seconds, Wan video 1933.33 seconds,
and ACE-Step music 160.53 seconds. The video contains 81 frames at 832 × 480,
16 fps; inspected frames show two adults on a bench in a sunny leafy park,
turning toward one another. The camera is mostly behind the people and the
colors are strongly saturated. Dialogue uses one narration voice, without lip
synchronization. The 5.85-second speech is not accelerated: the 94-frame final
timeline is 5.875 seconds and holds the last video frame for the remaining time.
Music and ambience levels were reduced, with short fades, before export.

Native OpenShot render `a54501bc-3323-4586-8a3d-efa35cda38f0` completed and its
MP4 was downloaded through the app: 768,274 bytes, H.264 video with audio,
SHA-256 `d84d7c9ac37bb73ba3b96fead5469877395e72207214313378e9d9f38090fd93`.
The mixed audio is non-silent (-25.6 dB mean, -9.1 dB peak). User copy:
`D:\ScriptStudio\ScriptStudioNative\downloads\Summer-Park-Bench-local-test.mp4`.
Paid calls: none. The authorized companion pause was reversed after GPU work.
Native Chrome verified all four populated media tracks, built the preview,
played and sought the 5.875-second video, and reported no page errors.
Observed UI issue: the rough script speech estimate includes bracketed visual
directions (about 34 seconds displayed versus 5.85 seconds of measured narration).
Actual production timing and the final export correctly exclude those directions.

### Planner and spoken-script parsing repair (2026-09-19)

- Replaced whole-script word counting and separate regex parsing with one backend
  parser shared by the editor, draft estimates, and both local planners. Nested,
  multiline, standalone, trailing, and unfinished visual notes have explicit
  behavior; escaped brackets remain spoken text. The editor cancels stale analysis
  requests and identifies unfinished directions before planning.
- Ollama plans visuals using ordered source-beat references, one scene per request.
  The app owns narration and rejects missing, repeated, or reordered references.
  The installed gemma3:4b rejects schema-constrained generation with a vocabulary
  error; an explicit compatibility path requests JSON, validates the same schema
  and coverage, and permits one bounded repair. No deterministic fallback or paid
  generation is used.
- Real native Windows gemma3:4b validation passed for the exact reviewed park-bench
  script (14 spoken words, ~6 seconds, one continuous shot, 4.84 seconds planning)
  and a two-scene nested/multiline-direction script (two shots, 3.42 seconds).
  Both retained every original spoken word and its order. Evidence is in
  `D:\ScriptStudio\ScriptStudioNative\workspace-local-models\planner-validation.json`.
- Current-source validation: 82 backend tests passed (three existing dependency
  deprecation warnings); PostgreSQL reservation/concurrency acceptance passed;
  frontend TypeScript/Vite build passed. All 12 browser cases passed across the
  full run and the corrected save/reopen regression rerun, including stale
  responses, notes-only scripts, incomplete notes, literal brackets, and the
  existing production/edit/preview/export workflow.
- The first desktop smoke test exposed an additional prompt ambiguity with the
  project's actual visual style: gemma3 treated source-beat indices as output-shot
  numbers. Validation rejected that response without changing the project. The
  prompt now includes a concrete example using all actual source indices, and
  repair feedback gives a direct coverage correction without Pydantic input dumps.
  Retesting with the exact project settings passed: park scene 3.48 seconds,
  two-scene script 4.55 seconds, all spoken text preserved.
- Final deployed implementation: `6d12a3e5f6f5a365d2ad87241ec1aea0343e9685`,
  native package `c931adacc1380dc2`, EXE SHA-256
  `a28f9f7582095c3704b8e0dbb19c6e9b1fc6c89ee45bfaa5ab5ee135f2ddc9e0`.
  The desktop shortcut launches the updated D: app. Upgrade comparison preserved
  all 79 project documents (including the validation project), four ready models,
  configured protected Hugging Face credentials, and the disabled paid master.
  The old runtime stalled during shutdown; its database was stopped cleanly before
  ending that process, and a read-only snapshot was compared after startup.
- Final native Chromium UI validation passed through the real Ollama planning
  endpoint using the exact park-project settings: one continuous shot, all 14
  spoken words preserved, editor estimate ~6 seconds, no page errors. The original
  park project remained unchanged; its exported MP4 still has SHA-256
  `d84d7c9ac37bb73ba3b96fead5469877395e72207214313378e9d9f38090fd93`.
  Evidence: workspace `planner-release-ui-verification.json`,
  `planner-release-verification.json`, `planner-park-estimate.png`, and
  `planner-live-storyboard.png`. Both desktop windows were visible, and the
  Minecraft companion was resumed and verified running after validation.

### Local-model installation visibility and durable reuse

- Add measured per-stage download, unpacking and verification progress, current
  file, elapsed time, independent installer heartbeat and connection warnings.
- Keep long unpacking operations cancellable between chunks; show indeterminate
  progress for work with no meaningful percentage instead of a frozen 100% bar.
- Reuse verified persisted installations on repeated Install requests and app
  restarts; distinguish installed files from per-generation RAM/VRAM loading.
- Validation: full backend suite passed (86 tests), followed by 13 focused tests
  including a new slow-step heartbeat check; PostgreSQL concurrency check and
  frontend production build passed. Native Windows Edge progress/reconnect/cancel/
  persisted-readiness interaction test passed. Packaged desktop verification passed.

- Native deployment preserved all 79 project documents and four Ready models.
  Repeated Install calls reused all four without changing their saved state.
  Split downloaded-file and installed-runtime verification labels after observing
  the real verification pass so per-stage percentage resets are explicit.

- Final native build `290aca2` deployed through the desktop shortcut; SHA-256
  `d6cf9eb271632cecccf241334b3c0d7fa62d8efe892ea64ecc3901ff1742d5ed`.
  Both release restarts preserved all 79 project documents and four Ready models.
  Windows Edge confirmed Installed/Repair controls, distinct verification labels,
  and repeated Install requests that left all four saved installations unchanged.
- Real Kokoro verification on the preceding progress build completed Ready with
  435 observed status samples, 238 distinct heartbeat updates, measured file
  progress, indeterminate runtime-probe feedback and no browser errors. The final
  refinement changes stage labels only; its 13 focused backend tests and native
  Edge stage-transition test passed. Final deployed browser smoke also passed.
- Local evidence: `D:/ScriptStudio/ScriptStudioNative/workspace-local-models/`
  `installation-progress-ui-verification.json`,
  `installation-progress-release-verification.json`, and
  `installation-progress-final-verification.json` (not tracked in Git).

### Queue phase progress without interrupting active jobs

- Implement reusable colored phase bars for production queue and export jobs,
  with legacy API support, measured step counts, reduced motion and both themes.
- Frontend build and isolated native Windows Edge interaction test passed.
- Deploy web assets only while Wan runs; retain old assets and record backend/Wan
  process identities. Backend progress instrumentation is prepared separately and
  must not be deployed until all queued and active jobs finish.

- UI-only deployment succeeded with backend PID 39924 unchanged. Wan completed
  naturally (all 30 generation steps) and its existing job remained Ready. Native
  Edge confirmed six completed phases and no browser errors; a separate tab was
  opened without reloading the user's existing editor.
- Add durable optional queue-progress metadata, sanitized bounded Wan loading
  counters, separate activity/contact timestamps, local file-saving phases and
  render/encode callbacks. Full backend suite passed 98 tests, followed by 29
  focused queue/job/render tests after retry/GPU-wait refinements. PostgreSQL
  concurrency and native Edge legacy/enhanced/multiple-provider fixtures passed.
- Complete native package deployment remains gated on an immediately rechecked
  empty active/queued set; never replace a running backend while jobs exist.

- Add completed-job Preview clip and Add to timeline controls. Clip playback uses
  its own clock so previewing cannot move the insertion point. Already-placed
  clips show On timeline; manual additions preserve existing items and use the
  existing revision-checked timeline API. Automatic placement rules stay intact.

- Add preview-driven timeline selection/scrolling and persistent clip renaming in queue, library and inspector. Native Edge fixtures passed highlight, rename and placement behavior. Bound native HTTP graceful shutdown so open SSE tabs cannot prevent shutdown; worker draining still completes before PostgreSQL stops.

- Final native release `f4e6341` deployed through the desktop shortcut; SHA-256
  `10a937ebb79fcc49707575a37e9e84e39b97064a82b81a2cf9b2188a37ad5507`.
  All 81 existing project documents and four installed-model ready states were
  preserved. The old idle backend needed recovery from an open SSE connection;
  zero active/queued jobs were rechecked before stopping it and PostgreSQL was
  shut down cleanly. The new package bounds HTTP shutdown while retaining worker
  draining. No running generation was interrupted.
- Native Edge live verification passed on a dedicated project: real Kokoro audio,
  explicitly mock visuals/music, actual rendered MP4 playback, timeline insertion,
  duplicate prevention, preview selection/highlight, persisted clip renaming, and
  preservation of existing timeline items. All jobs ended Ready with enhanced
  phase metadata. Focused rename/queue tests: 14 passed.
- Local evidence: workspace-local-models/queue-progress-release-verification.json,
  queue-native-verification.json and queue-ui-live-verification.json (untracked).

### Built-in 60-second local-model ScriptStudio demo

- Add a separate dashboard action using Kokoro, twelve Wan shots, and ACE-Step
  music; never substitute mocks or paid providers. Preserve the existing mock
  demo under an explicit label.
- Prepare an exact 60-second timeline with natural narration, captions, durable
  placeholders and automatic final export. Reconciliation is idempotent across
  restarts and respects failed jobs and manual timeline changes.
- Frontend build and 12 focused local-demo/job tests passed. Native deployment
  and real generation verification follow without interrupting existing jobs.
