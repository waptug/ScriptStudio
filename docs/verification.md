# Verification evidence

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
