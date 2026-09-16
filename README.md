# ScriptStudio

A local, single-user script-to-video studio with a React editor, durable Python
production services, and **OpenShot's actual video compositor**. Mock mode produces
playable narrated videos without any paid credentials.

## Start

Install Docker Engine/Desktop with Compose v2+ (WSL2 integration enabled on Windows).
Allow about 4 GB RAM and several GB of disk space for images and media.

```bash
cp .env.example .env
docker compose up -d --build
```

Open **http://localhost:8088**. Only the web port is published, bound to loopback.
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

1. Choose **Try the 60-second demo** or **New project** on the dashboard.
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

The demo creates a new project, runs real local synthesis and workers, renders both
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

- [Provider setup and documented capabilities](docs/providers.md)
- [Architecture and timeline invariants](docs/architecture.md)
- [OpenShot integration](docs/openshot.md)
- [Backup, restore, and security](docs/operations.md)
- [Known limitations](docs/limitations.md)
- [Verification evidence](docs/verification.md)

Do not expose this installation publicly without authentication, authorization,
TLS, CSRF protection, and upload/rate limits appropriate to your deployment.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE) and [third-party notices](NOTICE.md).
