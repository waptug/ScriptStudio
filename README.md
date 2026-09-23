# ScriptStudio

A local, single-user script-to-video studio with a React editor, durable Python
production services, and **OpenShot's actual video compositor**. Mock mode produces
playable narrated videos without any paid credentials.

## User documentation and quick start

- [Detailed user manual](docs/user-manual.md): step-by-step instructions for everyday use.
- [Download the Word .docx manual](frontend/public/ScriptStudio-User-Manual.docx).
- [Read the manual in a browser](frontend/public/user-manual.html).
- [Local AI demo](docs/local-demo.md) and [queue/clip controls](docs/queue-progress.md).
- Source and issue history: https://github.com/waptug/ScriptStudio

For the installed native Windows workspace, open the **ScriptStudio Local Models**
desktop shortcut (or `ScriptStudio-Local-Models.exe`). Keep the launcher open while
working. It starts the local services and opens the correct browser address; use
**Open studio** rather than a previously saved port. The native package needs no
separately installed Docker, Python or Node. Ollama is optional for script writing
and visual planning; media generation uses its own installed runtimes.

The **User manual** navigation link opens the guide and offers a Word download.
**About this project** links to this README, a browser-readable version, the manual,
and licensing information. Local copies of `README.md` and
`ScriptStudio-User-Manual.docx` are bundled with the application and available
through those links.

### Two different demos

| Dashboard action | Media sources | What happens |
| --- | --- | --- |
| Try the 60-second mock demo | eSpeak, labeled synthetic footage, synthesized music | Opens sample content for reviewing, planning and producing. |
| Create 60-second ScriptStudio demo · local AI | Kokoro narration, twelve Wan shots, ACE-Step music | Starts a separate introduction project, builds a 60-second timeline and queues final export when all generation is ready. |

The local AI demo requires the three models to be Ready in **Admin → Local models**.
It never falls back to mocks and does not enable paid providers. Its prompt is
“Introducing ScriptStudio and what it does.” Twelve five-second placements make
exactly 1,440 frames at 24 fps. Natural narration is not accelerated or cut; if it
exceeds a minute, assembly stops with an explanation. Manual edits are honored and
can change the preset duration. Allow several hours for Wan generation on a
consumer GPU; sixty seconds describes the finished video, not processing time.

### Queue progress, preview and clip names

Queue segments show the order of applicable phases: gray **Queued**, blue
**Prepare/Load model**, purple **Generate/Render**, cyan **Save/Download/Encode**,
amber **Check**, green **Ready**. Completed phases retain checkmarks; current work
is outlined; remaining phases are dimmed. Segment widths are not an ETA. Measured
steps, component counts, elapsed time and contact/activity information have distinct
meanings; an elapsed timer alone cannot establish that a model is progressing.

Ready jobs offer **Preview clip**, which plays the original media and highlights
its existing timeline placement without moving the insertion point. **Add to
timeline** inserts an unplaced asset at that point; **On timeline** prevents an
accidental second insertion. **Rename clip** in the queue, library or inspector
saves a readable asset name throughout the app without modifying its media file.
Use **Return to timeline preview** to return to the rendered project preview.

### Installation, loading and storage

Installed media models and isolated inference runtimes persist in
`ScriptStudioNative/local-models`. Normal generation does not download/install them
again when the pinned revision is unchanged. Loading those files into RAM/VRAM for
a generation process is still necessary. All four models are not kept resident
together, and runtime memory cannot survive a shutdown. GPU work shares the GPU
with other applications; duplicate submissions do not make a slow load faster.

The installed local-model workspace stores its database, projects and generated
media under `ScriptStudioNative/workspace-local-models`. Other launcher modes may
use a different data subfolder. Keep the EXE and complete `ScriptStudioNative`
folder together. Stop the app and wait for active work to drain before backing up
or moving native database files. Do not merge database directories or delete media
referenced by projects. Export important finished videos separately.

### Common problems

- **Old address will not connect:** reopen with the launcher and use its current URL.
- **Model unavailable:** check Ready, access conditions and errors in Admin; use Resume, Verify or Repair as appropriate.
- **Long Wan loading:** inspect activity and measured detail, available memory and disk; let healthy work continue instead of submitting duplicates.
- **Clip not placed automatically:** check its placeholder, lock/selected take and automatic-fill setting; add a ready asset manually if desired.
- **Preview stale:** rebuild after edits; individual clip playback is separate from the full timeline preview.
- **Final export blocked:** finish/select missing media or intentionally remove unwanted placeholders. Draft export is visibly unfinished.
- **Revision conflict:** refresh and reapply the intended edit; do not overwrite a concurrent completion blindly.

For support, include project name, short job ID, provider, state/phase and exact
error text. Logs live in the active native workspace. Review logs before sharing;
do not publish credentials or runtime configuration containing passwords.

## Docker development / server startup

Install Docker Engine/Desktop with Compose v2+ (WSL2 integration enabled on Windows).
Allow about 4 GB RAM and several GB of disk space for images and media.

```bash
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:8088**. Only the web port is published, bound to loopback.
Use **Light mode / Dark mode** in any page header to switch the interface theme.
Dark is the default; your choice is saved in this browser and shared across tabs.
If browser storage is blocked, switching still works for the current visit.
Change `SCRIPTSTUDIO_PORT` in `.env` if that port is occupied. Initial build installs
FFmpeg, eSpeak, libopenshot, Python dependencies, and frontend tooling. Subsequent
runs do not need an Internet connection in mock mode.

```bash
docker compose ps
docker compose logs -f worker
docker compose stop                 # stop, preserve all projects/media
docker compose up -d                # resume
docker compose down                # remove containers, preserve named volumes
```

**Do not use `docker compose down -v` unless you intend to erase your projects.**

## Standalone native Windows EXE

The native package is `artifacts/native/ScriptStudio-Native-Windows-x64.exe`.
It bundles Windows Python, PostgreSQL, OpenShot, FFmpeg, offline narration, and
the browser interface. Docker, WSL, Redis, installed Python, and Node are not
required to run it. Start studio from the launcher and keep that window open.
Closing it drains active work and stops its services. Data lives under the selected workspace directory in
`ScriptStudioNative` beside the EXE, separately from the Docker installation.

See [native packaging, operation, and build instructions](packaging/native/README.md)
and [validation evidence](docs/verification.md). The launcher uses the .NET
Framework included with Windows 10/11; the EXE is unsigned.

For local AI narration, music, and video, use **Admin → Local models** in the
native Windows app. See [the local-model usage guide](docs/local-models.md) for
Ollama writing/planning, Kokoro voices, ACE-Step music, Wan video, and
Stable Audio access requirements. Downloads and isolated inference runtimes stay
beside the EXE. Local generation is separate from mock and paid providers.

## Earlier Docker-based Windows EXE package

Build an offline Windows application package with
`python3 packaging/windows/build.py` after building the Compose images. Output:
`artifacts/windows/ScriptStudio-Windows-x64.exe`, with a SHA-256 checksum and image
manifest alongside it. The single EXE includes the app images, matching application
source, and notices. It still requires a running **Linux Docker engine and Compose
v2**, either Docker Desktop or Docker in a running WSL distribution; it is not
a Docker-free native port. Double-click it and choose **Start studio**.

The launcher keeps desktop data separate from this checkout, selects a loopback
port, and provides Start/Stop/Open controls. No user projects or credentials are
bundled. See [Windows packaging and operation](packaging/windows/README.md).

## Create a video

You can write manually or use **Script → Write with AI**. Enter a video idea,
audience, tone, and target duration, then generate a draft. Edit it in the review box
and choose **Use this script** (or **Replace script with this draft**). Generation
never overwrites your script automatically. Save the accepted script or choose
**Plan scenes & shots** to continue. Prompt/draft review state is kept in this
browser per project; the accepted script is stored on the server when saved.

Open **Admin** from the dashboard or editor to configure the local Ollama URL,
list installed models, and select separate script-writing and scene-planning models.
Admin also stores Runway/ElevenLabs model names, cost estimates, and encrypted API
credentials. Blank key fields keep existing keys; explicit Clear controls remove them.
Saved Admin settings override environment defaults and apply to new requests without
restarting containers. Existing jobs retain their captured model. Under **Admin →
Paid AI generation**, enable the master switch and the specific text, video, audio,
speech, or music permission, then save. All category permissions default off.
Credentials, supported adapters, and project budgets are still required. Turning off
blocks new submissions, including queued jobs; already-submitted jobs can finish.

See [Admin configuration](docs/admin.md) for credential storage and setup details.

1. Choose **Try the 60-second mock demo** or **New project** on the dashboard. The separate local AI demo starts its own production automatically.
2. In Project settings choose output format, visual style, voice/music providers,
   spending ceiling, and generation concurrency. Save settings. The target duration
   is advisory; actual narration determines timing. Set FPS before production.
3. Write narration in paragraphs. Put unspoken visual instructions in `[brackets]`.
   Save the script, then **Plan scenes & shots**. Review/edit each scene and prompt.
4. **Start production**. Narration is generated and measured first; shot placeholders
   and captions are then created. Completed videos fill their associated placeholders.
5. Edit the timeline: drag clips, select an item for exact frame-based move/trim,
   split at the ruler playhead, duplicate/delete, mute/lock, fades/volume, transform,
   or select a different take. Undo/redo is persisted. The ruler seeks the preview.
6. Import footage, PNG/JPEG references, music, or sound effects through **Media**.
   Use its track selector to place imported assets. Regenerate shots in Storyboard;
   the old take remains selected until you explicitly choose another in Inspector.
7. **Build preview** after edits. This creates a synchronized proxy-resolution MP4
   from the same OpenShot/FFmpeg timeline used for export. The revision badge tells
   you when the preview is stale. Seeking/playback use the browser video player.
8. **Export → Render final MP4**. Missing media blocks final export. Draft mode
   permits visibly labeled visual placeholders. Download MP4, SRT, WebVTT, or the
   **Continue in OpenShot** project bundle. Rendering uses an immutable revision.

Export downloads use `Project name_YYYY-MM-DD_HH-MM-SSZ` with the appropriate
`.mp4`, `.zip`, `.srt`, or `.vtt` extension. The timestamp is the render creation
time in UTC. New renders capture the project name; older renders use its current
name. Filename-unsafe characters are replaced and long names are shortened.

Mock mode uses eSpeak speech, clearly labeled synthetic footage, and a locally
synthesized instrumental bed. It does not claim to be live AI generation. Estimated
mock word timings are labeled; ElevenLabs alignment is retained when available.

## OpenShot reuse

`libopenshot` owns visual composition, native clip/keyframe handling, alpha fades,
transforms, and frame rendering. Its Python bindings run in an isolated system-Python
process. FFmpeg normalizes clips, explicitly extends coverage, mixes audio with
sidechain ducking, and encodes the final MP4. Preview/export share this pipeline.

Every final render includes a ZIP containing a native `.osp` file and its media.
Extract **the entire ZIP** before opening `ScriptStudio.osp` in OpenShot. Individual
visual clips and native transform/fade keyframes remain editable. Titles/captions
are transparent image clips. Source trims/hold/loop coverage are normalized.
Finishing audio is supplied as one exact mix, with original narration, music, effects,
and alternate takes also in the library. Desktop changes do not sync back to the web
app. See [OpenShot integration](docs/openshot.md) for compatibility and provenance.

## Reproduce the demo and tests

With the Compose stack running:

```bash
docker compose exec -T api python tools/demo.py
docker compose run --rm --no-deps api pytest -q -p no:cacheprovider
docker compose exec -T api python -m tools.postgres_concurrency
```

The command-line mock demo creates a new project, runs eSpeak and synthetic-media workers, renders both
preview and final MP4, verifies durations and HTTP range playback, and downloads the
OpenShot bundle. It prints project/job/asset IDs. It never enables paid providers.

Browser smoke (Node 22+ on the host):

```bash
npm ci --prefix frontend
npx --prefix frontend playwright install chromium
npm run test:browser --prefix frontend
```

The browser test creates a short project, produces footage, edits a title, checks
undo/redo and reload, plays/seeks a preview, and exports MP4 plus OpenShot handoff.
It writes a screenshot to `frontend/test-results/editor.png`.

For real restart recovery (stop ordinary editing while this test runs):

```bash
docker compose stop worker beat
docker compose exec -T api python -m tools.restart_fixture prepare
docker compose restart redis
docker compose start worker beat
docker compose exec -T api python -m tools.restart_fixture verify
```

Unit tests cover out-of-order completion, moved/deleted/locked placeholders, duplicate
completion, alternate takes, unknown submissions, download retry without regeneration,
measured narration timing, revision conflicts, undo/redo, media validation, frame rates,
and preview/export synchronization. The PostgreSQL test uses simultaneous transactions
for real row-lock budget/concurrency enforcement. Tests create clearly labeled fixtures.

## Development

Backend code is under `backend/studio`, typed contracts in `schemas.py`, database
migration in `backend/migrations`, tests in `backend/tests`. Thin FastAPI routes are
backed by focused services. OpenAPI is available at `/api/openapi.json` and interactive API docs at `/api/docs`.

```bash
npm run build --prefix frontend
docker compose build
docker compose up -d
```

Pin updates are deliberate: Python direct dependencies are in `requirements.txt`,
resolved dependencies in `requirements.lock`, npm dependencies in `package-lock.json`.
The default database is PostgreSQL; SQLite is used only for isolated unit tests.

## Documentation

Open **About this project** from the dashboard or editor for foundation credits,
the GPL-3.0-or-later project license, searchable component versions and licenses,
and collected copyright notices. The inventory includes transitive dependencies
and container system packages, with optional tools and source-available Redis
clearly identified. See [third-party notices](NOTICE.md) for inventory scope and
the refresh procedure after dependency changes.

The same page includes **Recreate ScriptStudio with Codex**: read, copy, select,
or download a self-contained `/goal` specification. Its canonical source is
`frontend/public/codex-goal.txt`; the page, clipboard, and download use that one
file. It covers functionality, invariants, the zero-dollar generation ceiling,
and verification requirements. Use it in the Codex workspace where you intend
to build; copying does not execute it. It specifies a functional recreation,
not identical source code. See [OpenAI's goals guide](https://learn.chatgpt.com/use-cases/follow-goals).

- [Provider setup and documented capabilities](docs/providers.md)
- [Architecture and timeline invariants](docs/architecture.md)
- [OpenShot integration](docs/openshot.md)
- [Backup, restore, and security](docs/operations.md)
- [Known limitations](docs/limitations.md)
- [Verification evidence](docs/verification.md)

Do not expose this installation publicly without authentication, authorization,
TLS, CSRF protection, and upload/rate limits appropriate to your deployment.

## License

The matching vector mark is in `frontend/public/logo.svg`; the multi-resolution
Windows/browser icon is `frontend/public/favicon.ico` (16–256 pixels). Both are
available to download from **About this project**. The SVG uses paths with no font
dependency. After editing it, run `node scripts/generate_icon.mjs` to rebuild the
ICO using the frontend's existing Playwright/Chromium installation.

GPL-3.0-or-later. See [LICENSE](LICENSE) and [third-party notices](NOTICE.md).

### Automatic Ollama setup

On opening the dashboard or Admin, ScriptStudio checks the saved Ollama URL,
`OLLAMA_HOST` (including the Windows user environment), loopback port 11434, and
the Docker host address in container installations. A reachable server is verified
using `/api/tags`; its URL is saved automatically only if no URL is configured.
Existing URLs are preserved, with **Use detected URL** available in Admin.
Installed local models populate the model choices; choose writing/planning models
and save. Discovery never generates content, downloads models, or calls cloud AI.
If Ollama is unreachable, the setup notice links to the official installer and
asks you to open Ollama and retry. If it has no local models, the notice asks you
to download one in Ollama. Manual writing and mock production remain available.

The AI script writer shows an activity panel while a draft request is pending, with
a spinner, an indeterminate progress bar, and elapsed waiting time. It reports
success or failure without replacing your saved script. Elapsed time is not a
model completion estimate; internal model reasoning is not displayed.

### Portable Windows storage and free space

The native launcher resolves its EXE folder, independently of the current working
directory. Runtime packages, PostgreSQL, projects, logs, temporary files, caches,
and the dedicated Edge/Chrome browser profile stay in `ScriptStudioNative` beside
the EXE. Browser downloads default to `ScriptStudioNative/downloads`. Move the
EXE and that folder together while the launcher is closed. The browser profile
is separate from your usual browser; Windows and separately installed Ollama
remain responsible for their own system files and model storage.

Before extraction, the launcher checks free space on the actual destination
volume for the expanded archive (plus filesystem overhead) and 2 GiB of working
space. Cached launches require 2 GiB free. It reads the ZIP directly from the
EXE, without creating a second compressed copy. Insufficient space shows required
and available space and closes the launcher after acknowledgement, before any
services start. The 2 GiB reserve is a startup minimum, not an estimate of space
needed for arbitrary future video projects. Use a writable local folder.

Older versions stored projects in `%LOCALAPPDATA%\ScriptStudioNative\data`.
To retain those projects, stop and close the old launcher, then move that complete
`data` directory into the new `ScriptStudioNative` folder **before first start**.
Do not merge two database directories. The launcher identifies legacy data but
never copies a potentially running database or deletes existing projects.

### Regenerate bundled documentation

The Markdown sources are `README.md` and `docs/user-manual.md`. After editing them,
regenerate the browser guides and Word download before building the frontend:

```bash
python3 -m venv /tmp/scriptstudio-docs
/tmp/scriptstudio-docs/bin/pip install -r scripts/docs-requirements.txt
/tmp/scriptstudio-docs/bin/python scripts/generate_user_docs.py
npm run build --prefix frontend
```

The generated files in `frontend/public` are committed so normal application
builds and native packages include the guides without document conversion tools.

Automatic native render-session resource reservation and restoration are described
in [resource optimization](docs/resource-optimization.md).
