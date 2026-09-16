# Working in ScriptStudio

ScriptStudio is a local script-to-video application with React/TypeScript, FastAPI,
PostgreSQL, Celery/Redis, persistent local media, libopenshot, and FFmpeg.

## Boundaries and invariants

- `backend/studio/api.py` is the thin HTTP layer; keep business logic in focused services.
- PostgreSQL owns job state. Redis carries wakeups; it is never the durable source of truth.
- Acquire the project row lock for edits, job reservations/claims, and automatic placement.
- Background completion may only fill its surviving eligible placeholder. Never move,
  trim, resurrect, unlock, or replace a user-selected take. Regeneration preserves history.
- Timeline positions are integer frames with rational FPS. Never accelerate narration
  to fit footage. Preview and export use the same immutable timeline specification.
- Reuse libopenshot for visual composition and native serialization. Keep its binary
  bindings in the system-Python subprocess; do not import them into Python 3.12 services.
- Serialize OpenShot clip readers before adding clips to a timeline (AddClip inserts
  a runtime FrameMapper that cannot be saved as a portable source reader).
- Never retry an uncertain paid submission blindly. Keep provider IDs, download retries,
  cost reservations, and operator reconciliation independent of new generation.
- Keep mock mode visibly labeled. Never claim live provider validation from mocks.
- No paid calls without explicit authorization and a defined spending ceiling.

## Validation

```bash
docker compose run --rm --no-deps api pytest -q -p no:cacheprovider
docker compose exec -T api python -m tools.postgres_concurrency
npm run build --prefix frontend
npm run test:browser --prefix frontend
```

Rebuild images when testing changed container code, or mount `backend:/app:ro` for
isolated test runs. Full demo: `docker compose exec -T api python tools/demo.py`.
Setup and restart verification commands are in README. Update documentation and
PLAN.md when behavior or evidence changes. Preserve unrelated user work; exclude
credentials, generated media, caches, screenshots, and backups from Git.
