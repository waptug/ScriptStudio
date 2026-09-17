# Verification evidence

## Windows offline application package

Verified on 2026-09-16 using the actual Windows x64 executable, the Windows .NET
Framework compiler/runtime, and Docker in the running Ubuntu WSL distribution.
The package is one approximately **487 MB (465 MiB)** EXE containing four Linux
runtime images, source, and notices. Docker/WSL and the Windows framework runtime
are external prerequisites; this is not a native Docker-free Windows application.

- Actual Windows extraction tests passed for a valid payload and correctly
  rejected checksum corruption, archive traversal, and missing required files.
- The bundled gzip image archive loaded successfully with `docker load`.
- Windows EXE `--start-test` started a separate `scriptstudio-exe-test` stack and
  verified HTTP health at `http://127.0.0.1:18089`. No developer volumes, credentials,
  or media were copied into it. The package's paid-generation defaults are off.
- Inside the packaged backend: **44 tests passed (78.10 seconds)** and PostgreSQL
  concurrency checks passed. Against its actual web endpoint: **8 Chromium tests
  passed (1.2 minutes)**, including local mock production, editing, video playback,
  all export downloads, Admin, themes, credits, and prompt copy/download behavior.
  The frontend source build passed too.
- Actual Windows EXE Stop/Start preserved all **5 test projects and their
  revisions**. Test services were stopped afterward without deleting their volumes.
  The regular development installation remains separate.
- The native Windows launcher was rendered and captured. Testing exposed fixes
  for Windows/WSL option quoting, detection of Docker in running distributions,
  and icon loading from UNC paths. The build/test helpers use WSL's explicit
  interoperability loader when binfmt registration is unavailable, without
  altering system configuration. An occupied test port was avoided without
  stopping the existing service.

Build instructions and runtime boundaries are in
[Windows packaging](../packaging/windows/README.md). Generated EXE, SHA-256 file,
manifest, test reports, and screenshots live under ignored `artifacts/windows/`.
The EXE is unsigned. Docker Desktop, clean-PC setup, Windows ARM, and a fully
native Windows media stack have not been tested. Compilation alone is not the
basis of the startup claim; a real Windows process started the verified stack.

## Interface themes & Codex replication prompt

Verified locally on 2026-09-16. Every page header has a dark/light toggle; dark
remains the default. A pre-render script restores the saved browser preference.
The light palette covers forms, panels, timeline tracks/clips, states, and About
content, while the video viewing surface remains dark. Theme selection persists
across reloads, synchronizes tabs, and remains usable when storage is blocked.

About now includes a self-contained replication specification from the canonical
`frontend/public/codex-goal.txt`, with read/copy/select/download controls. The
command format was checked against [OpenAI's goals guide](https://learn.chatgpt.com/use-cases/follow-goals).
The prompt defines functional reconstruction and acceptance evidence, not identical
source or media output. No replication goal was launched as part of this change.

- Frontend production build, **44 backend tests (11.66 seconds)**, PostgreSQL
  concurrency checks, and **8 Chromium tests (30.2 seconds)** passed.
- Theme coverage includes keyboard activation, actual computed surface/clip colors,
  preference reload, unsaved script preservation, all page headers, cross-tab
  changes, blocked storage, and mobile overflow. Light editor/About screenshots
  were visually inspected. Browser coverage caught and resolved an unintended
  duplicate theme button in the timeline toolbar before final verification.
- Prompt tests compare displayed text, real clipboard contents, and downloaded
  bytes; check the text MIME type; and verify clipboard denial opens/selects the
  complete text for manual copying.
- Rebuilt and deployed the local web image. `/api/health` returned `status: ok`
  with paid generation disabled. No provider calls or new dependencies were added.

## Matching SVG & ICO brand assets

Verified locally on 2026-09-16. The original lime-green slanted S mark is now a
font-independent SVG used in dashboard, editor, Admin, and About headers. Browser
icons use the same SVG with an ICO fallback; About offers downloads of both assets.

- Inspected the rasterized mark and deployed About header visually. Checked the
  ICO directory and PNG dimensions for all seven 32-bit frames: 16, 24, 32, 48,
  64, 128, and 256 pixels. `node scripts/generate_icon.mjs` regenerates the ICO.
- Live Chromium check confirmed the SVG decodes, both favicon declarations exist,
  asset MIME types are correct, and both downloads complete with their filenames.
- Frontend build, **44 backend tests (11.48 seconds)**, PostgreSQL concurrency
  checks, and **4 Chromium tests (27.4 seconds)** passed. Rebuilt and deployed the
  local Compose stack successfully. No new dependencies or paid calls were used.

## About this project & attribution

Verified locally on 2026-09-16. Dashboard and editor buttons open foundation
credits, the project GPL-3.0-or-later license, and a searchable component inventory.
Redis 7.4.2 is identified as source-available under RSALv2 or SSPLv1; optional
tools, model licenses, and proprietary integrations are distinguished.

- Generated **763 component/license-text records** and **339 distinct collected
  notices** from the npm lockfile, installed Python distributions, Debian api/db
  packages, and Alpine web/redis packages, plus foundation/optional tool entries.
  All Debian package records have a collected copyright notice. Shared documents
  and license texts are deduplicated; full notices load on demand. Scope and
  missing embedded notices for other groups are disclosed in the UI.
- Verified every notice reference resolves and the public GPL/NOTICE copies
  match repository originals. Re-running the generator reproduced the deployed
  inventory. `ffmpeg -L` identified the installed build as GPL-2.0-or-later.
- Frontend production build, **44 backend tests (12.00 seconds)**, and PostgreSQL
  concurrency checks passed. **4 Chromium tests passed (24.4 seconds)**, covering
  About navigation, keyboard focus/Escape return, search/filter, MIT notice text,
  inventory download and content types, empty search, mobile overflow, unsaved
  script preservation, and the existing local video workflow.
- Rebuilt/deployed Compose successfully. The mobile About screenshot was visually
  inspected (`frontend/test-results/about-mobile.png`, ignored). The initial
  About test needed its filter selector relaxed because the enclosing label also
  contains option text; no application failure was observed in that check.

## Export download names

Verified locally on 2026-09-16. MP4, OpenShot ZIP, SRT, and WebVTT downloads
share a safe project name and UTC render creation timestamp. New renders capture
the project name; older renders fall back to the current name.

- Backend suite: 43 existing tests passed. The new download test initially failed
  because its legacy-name assertion did not decode URL-encoded spaces; after
  fixing the assertion, the new test passed. It checks all four response filenames,
  Unicode and unsafe characters, captured names after renaming, old exports, and
  unchanged inline media byte-range responses.
- Frontend production build and PostgreSQL concurrency checks passed.
- Chromium: **3 passed in 27.8 seconds**, including actual downloads of all four
  formats with matching suggested filenames and no download failures.
- Rebuilt and deployed using `docker compose up -d --build`. The local health
  endpoint returned `status: ok` with paid generation disabled.

## Paid generation controls

Verified locally on 2026-09-16 using the current source and rebuilt Compose images.

- Backend suite: **43 passed in 13.27 seconds**, with three dependency deprecation
  warnings. The source was mounted read-only into the test container. Permission
  tests cover defaults, persistence, independent categories, master override,
  direct adapter gates, project budgets, blocking queued submissions, explicit
  retry, and continued polling of an existing provider task after disabling.
- TypeScript/Vite production build passed. PostgreSQL concurrency checks passed
  for simultaneous budget reservations and job claims.
- Chromium suite: **3 passed in 24.1 seconds**. The paid-controls test exercised
  every switch, save/reload, and master override using intercepted Admin responses;
  it never enabled paid generation in the running server. Actual API persistence
  is covered by the isolated backend tests. The other browser tests verified the
  script review flow and real local mock production, timeline editing, preview
  playback/seeking, final export, and the OpenShot handoff link.
- `docker compose up -d --build` completed; API, worker, beat, web, PostgreSQL,
  and Redis are running. The loopback `/api/providers` endpoint reported the
  master and all five categories disabled. No paid provider requests were made.

## Prompt-to-script and Admin follow-up

The follow-up added separate workflow model selection, installed-model discovery,
encrypted Runway/ElevenLabs credentials, and an optional prompt-to-script review flow.
Migration `002_admin_settings` applied successfully to the existing PostgreSQL database.

- Backend suite: **34 passed in 11.69 seconds**. New coverage includes encrypted
  storage, write-only credential responses, replace/clear behavior, environment-key
  override, actual provider header lookup, cross-origin rejection, redacted validation
  failures, model selection, draft isolation, invalid/truncated output, and model discovery.
  After normalizing standalone visual directions onto their narration paragraphs,
  the affected Admin/writer/provider tests were rerun: **14 passed in 1.83 seconds**.
- Existing Chromium production/edit/preview/export test passed (28.5 seconds).
- New Chromium Admin/writer test passed (1.0 minute): save/reload model choices,
  preserve manual text during generation, review/edit/apply a draft, save and plan it,
  and retain the prompt/draft across tab changes. Model output in this browser test
  is a deterministic HTTP fixture; settings saves and script planning use the real API.
- Real local inference: installed **gemma3:4b**, Ollama **0.21.1**, draft endpoint
  returned HTTP 200 with an approximately 35-second herb-gardening script. Project
  `86d8a1d8-31b8-4205-a04f-9a978c56774e` retained its original saved script after generation.
  No paid provider was called. Draft estimates are word-count estimates, not measured audio.
- Live `/api/tags` discovery from the API container succeeded. Structured JSON requests
  failed on this local Ollama installation with a vocabulary-loading error. Writing
  uses plain prose; deterministic scene planning remains available. Live AI storyboard
  planning is not claimed as verified.
- TypeScript/Vite build passed. The updated Python dependency audit, including
  cryptography 50.0.1, reported no known vulnerabilities.

Admin uses the same local single-user boundary as the app. Keys are encrypted at rest,
not shown again after saving, and only decrypted server-side for provider use. No real
paid-provider key was entered during tests. The existing server live-mode spending gate
remains disabled. See [Admin setup and backups](admin.md).

## Original implementation verification

Verified locally on 2026-09-15 (America/Los_Angeles), using Docker Compose on Linux/WSL.
All generation used local mocks. No paid provider requests were made.

## Automated coverage

`docker compose run --rm --no-deps api pytest -q -p no:cacheprovider`:
**27 passed in 10.18 seconds**. Two third-party TestClient deprecation warnings remain;
they do not affect the passing assertions. Tests use isolated SQLite databases and
real FFmpeg, eSpeak, and libopenshot where media behavior matters.

| Acceptance condition | Evidence |
| --- | --- |
| Out-of-order results fill their own placeholders | `test_out_of_order_move_delete_duplicate_completion_and_takes` |
| Manual moves/trims survive completion; deletion prevents reinsertion | Same assembly test, plus lock/conflict tests |
| Duplicate completion is harmless | Same assembly test |
| Regeneration retains the selected previous take | `test_regeneration_workflow_retains_selected_take` |
| Download retries do not regenerate | `test_download_retry_keeps_original_generation` |
| Unknown submission never blindly resubmits | `test_ambiguous_submission_is_never_resubmitted` |
| Known rejection and rate limits are distinct from uncertain acceptance | Submission rejection and bounded-backoff tests |
| Pending and unknown charges reserve budget | `test_budget_counts_pending_unknown_and_canceled` |
| Reload, undo/redo, split, locks, revision conflicts | Timeline tests and browser workflow |
| A later automatic take survives undoing an earlier move | `test_undo_move_preserves_later_automatic_take` |
| Actual narration determines scene durations | `test_measured_narration_builds_placeholders_before_video` |
| Preview/export match timing and preserve fixed snapshots | `test_preview_export_duration_audio_and_immutable_snapshot` |
| Rational frame rates, portrait/square transforms and overlays | Parameterized native geometry tests |
| Audio samples begin at the intended timeline frame | `test_audio_content_starts_on_timeline_frame` |
| Missing media blocks final export | Render and API tests |
| Upload validation, cross-project isolation, traversal/download restrictions | API, timeline, and storage tests |
| Native handoff survives relocation | Export test reloads bundled `.osp` into libopenshot and renders three frames |

`python -m tools.postgres_concurrency` additionally passed against the running
PostgreSQL service: two simultaneous budget reservations admitted only one request;
two simultaneous claims with concurrency one admitted only one job. These are real
row-lock transactions, separate from SQLite unit tests.

The restart fixture passed with worker/beat stopped, Redis restarted, and workers
started again. The existing submitted job became ready with its original provider ID,
one submission attempt, and one timeline placement. This is actual process/service
restart evidence with mock generation, not a live provider recovery claim.

`npm run test:browser --prefix frontend`: **1 passed (1.3 minutes)** in Chromium.
The browser created/planned/produced a project, edited title text, used undo/redo,
reloaded saved edits, played and sought a proxy preview, and rendered a final export.
It added a second title while export ran and verified the completed export retained
its captured revision while the project revision advanced. No page JavaScript errors
were observed. Screenshot: ignored `frontend/test-results/editor.png`.

Two failures were resolved during verification: Nginx retained an old API address
after container replacement (fixed with runtime Docker DNS resolution), and the smoke
test attempted an edit while other initial assets were still arriving (the server
correctly rejected a stale revision). The smoke now waits for initial production to
finish; separate tests explicitly exercise background completion/edit conflicts.

## Render and desktop evidence

The reproducible sample produces four narration segments, twelve shots, and music
(17 source assets). A completed 55.042-second run produced both preview and final MP4;
HTTP byte-range playback returned 206, and the portable OpenShot ZIP downloaded.

The final rebuilt stack repeated the full workflow with measured narration rounded
up to frame boundaries: **55.125 seconds** for both preview and export, 12 shots,
17 source assets, and a 15,215,150-byte handoff ZIP. Project:
`6bdd8be5-d6d9-46a2-815f-4e393dbb8b8e`; preview:
`7c0e150a-d633-4f85-b02e-f30bef173215`; final:
`1d014d56-306b-4fb3-9849-e8eb96746e59`. The demo checked source placement, measured
output durations, MP4 range responses, and ZIP download before exiting successfully.

Desktop verification used project `8cd1679d-25fa-445a-8f58-c42938ec952e`, final render
`d80a3aa8-bde4-420a-96fb-8870ffe5004f`. The actual Linux OpenShot **2.6.1** desktop editor
opened the extracted bundle under Xvfb with networking disabled. Its log confirmed
project loading; the screenshot showed populated media, timeline clips, and a preview
frame with captions. Local evidence is retained in ignored `artifacts/openshot-desktop.png`
and `.log`. Offline update-check errors are explicitly excluded by the smoke checker.
Windows, macOS, and newer OpenShot versions were not tested.

## Dependency and deployment checks

The frontend TypeScript/Vite production build passed. `npm audit` reported zero known
vulnerabilities. `pip-audit --disable-pip --no-deps -r requirements.lock` reported no
known vulnerabilities for the pinned Python dependencies. These audits are snapshots,
not an audit of every OS package or a guarantee of security.

The Compose stack runs at `http://localhost:8088`, bound to loopback, with PostgreSQL
and media in persistent named volumes. Nginx uses Docker DNS with a five-second cache
so backend container replacement cannot leave a permanently stale upstream address.
After forcibly recreating the API container without restarting Nginx, the public
`/api/health` endpoint returned `{"status":"ok","live_enabled":false}`.

## External integration boundaries

Runway and ElevenLabs request/response contracts were tested through HTTP fixtures,
including provider task IDs, timestamp alignment, polling, and cancellation behavior.
Their live APIs were not called. Live operation requires server-side API keys, enabled
account/model/voice access, explicit spending authorization, configured rate estimates,
and a project budget. See [provider setup](providers.md).

Suno remains explicitly disabled because official API/account access was not verified;
music import works. Ollama structured planning was fixture-tested; a reachable local
server and installed local model are required for a live planner check. No cloud LLM
service or live Ollama model was used in acceptance testing.
