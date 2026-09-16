# Operations, backup, and restore

## Storage and networking

Compose creates named `scriptstudio_database` and `scriptstudio_media` volumes.
Originals, generated takes, previews, renders, subtitles, and provider metadata persist
across container replacement. PostgreSQL is authoritative; Redis can be recreated.
The web port defaults to `127.0.0.1:8088`. Database, Redis, and API have no published
host ports. The application has no authentication: do not expose it publicly until
adding authenticated authorization, TLS, CSRF protection, and resource/rate controls.

Provider secrets can be saved encrypted through Admin or supplied as server environment
variables. Never put real keys in Git. Back up your `.env` separately in a secure location.
The media backup must retain `.credentials/master.key` to decrypt saved Admin keys;
protect both database and media backups. See [Admin configuration](admin.md).
Normal API responses do not expose
keys or temporary provider media URLs. FFmpeg is always invoked with argument arrays;
script and title text is never shell code. Downloads require authorized HTTPS hosts
and public IP addresses, disallow redirects, and are size-bounded. Uploads use generated
storage paths, an extension allowlist, ffprobe plus full decode, and a 512 MiB limit.

## Consistent backup

Stop writes while taking both snapshots. Run from the repository root:

```bash
mkdir -p backups
docker compose stop web api worker beat
docker compose exec -T db pg_dump -U studio -d studio -Fc > backups/database.dump
docker run --rm -v scriptstudio_media:/data:ro -v "$PWD/backups:/backup" alpine:3.21.3 tar czf /backup/media.tar.gz -C /data .
docker compose start api worker beat web
```

Copy both files off the workstation, together with the matching source commit and
securely stored environment configuration. Add `backups/` to local exclusions (the
repository ignores it). Database-only or media-only backups are incomplete.

## Restore into a separate installation

Use a separate checkout/folder and a new Compose project name, so you do not overwrite
your original installation. Restore the same application version before upgrading.

```bash
docker compose -p scriptstudio-restore up -d db redis
docker compose -p scriptstudio-restore exec -T db pg_restore -U studio -d studio --no-owner < backups/database.dump
docker volume create scriptstudio-restore_media
docker run --rm -v scriptstudio-restore_media:/data -v "$PWD/backups:/backup:ro" alpine:3.21.3 tar xzf /backup/media.tar.gz -C /data
SCRIPTSTUDIO_PORT=8089 docker compose -p scriptstudio-restore up -d --build
```

Open localhost:8089 and verify project names, asset playback, timeline revisions,
and a draft render. Existing remote job IDs resume monitoring; uncertain submissions
remain unknown. Do not run two restored copies with live generation credentials at
once unless you deliberately intend to operate both queues.

## Recovery and diagnostics

```bash
docker compose logs --tail 100 api worker beat
docker compose exec -T api alembic current
curl http://localhost:8088/api/health
```

Normal polling/download errors back off and eventually become failed. Queue → Retry
reuses the saved provider task/result. Unknown live submission never automatically
resubmits. Reconcile Runway with its existing task ID. For synchronous narration,
recover/download the audio from the provider history, import it in Media, and choose
that asset under the failed/unknown job's recovery selector. Reservations remain
conservative where charges cannot be verified.

An interrupted worker can leave a lease for up to ten minutes. Wait for reconciliation;
do not manufacture a second paid job to shorten that wait. A ready narration job with
an assembly error usually indicates insufficient remaining budget or unsupported video
settings; correct the project settings and Beat retries assembly without new narration.

Render directories retain `openshot.log`, `ffmpeg.log`, native clip JSON, and the exact
filter graph. User-visible queue errors include a bounded error excerpt. Do not treat
these logs as safe to publish without reviewing project text and file paths.
