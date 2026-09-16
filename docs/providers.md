# Provider configuration

No paid API request was authorized or made during development. Mock mode is the
startup default. Environment variables stay server-side; `.env` is ignored by Git.

Before enabling live generation, obtain explicit operator authorization and a defined
USD limit, set `LIVE_GENERATION_ENABLED=true`, configure credentials/rates in `.env`,
restart with `docker compose up -d`, and set a project spending ceiling. The server
refuses requests with unavailable estimates or insufficient budget. Estimates include
pending and unknown requests and are labeled; actual billing may differ. Keep a
conservative margin. Server live mode is an authorization gate, not a billing oracle.

## Runway

Official references inspected during implementation:

- [Getting started](https://docs.dev.runwayml.com/guides/using-the-api/)
- [API reference](https://docs.dev.runwayml.com/api/)
- [Input limits](https://docs.dev.runwayml.com/assets/inputs/)
- [Pricing](https://docs.dev.runwayml.com/guides/pricing/)

Configure `RUNWAY_API_KEY`, `RUNWAY_MODEL=gen4.5`, and a conservative
`RUNWAY_USD_PER_SECOND`. The checked gen4.5 rate was 12 credits/second, with credits
priced at USD 0.01; the example uses USD 0.12/second. Verify your current account rate
before enabling generation. The adapter supports the documented gen4.5 contract:
`POST /v1/image_to_video`, optional `promptImage`, `promptText`, `ratio`, duration
2–10 integer seconds, bearer authorization and `X-Runway-Version: 2024-11-06`.
Polling uses `GET /v1/tasks/{id}`; cancellation uses `DELETE /v1/tasks/{id}`.
Model names are configurable, but a model with a different contract requires a new
capability implementation rather than blindly changing its name.

Text-only generation supports landscape `1280:720` and portrait `720:1280`. Square
`960:960` requires an imported reference image. Reference data URIs are generated
server-side; only project-owned validated images may be used. Camera instructions
are included in the textual prompt, not sent as an invented API parameter.

Provider results are downloaded immediately after completion. `DOWNLOAD_HOSTS` is an
explicit HTTPS CDN allowlist. If the provider returns a different CDN, a download
fails safely; authorize the verified host and retry the existing job. No paid request
is repeated. Redirects, private/reserved network addresses, credentials in URLs, and
non-443 ports are rejected. Keep this allowlist narrow.

If submission is uncertain, find its task ID in your provider account/history and
use Queue → Reconcile existing task. If you cannot establish the outcome, leave it
unknown; never blindly press a paid regenerate button to recover a lost response.
Cancellation cannot promise refunds, and cost reservations are retained conservatively.

## ElevenLabs narration

[Official timestamped speech API](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)

Configure `ELEVENLABS_API_KEY`, `ELEVENLABS_MODEL=eleven_multilingual_v2`, and
`ELEVENLABS_USD_PER_CHARACTER` using your plan's conservative cost. There is no default
universal character price because plans differ. Choose your actual voice ID from
ElevenLabs; the mock `en-us` voice ID is not an ElevenLabs voice.

The adapter calls `POST /v1/text-to-speech/{voice_id}/with-timestamps` with `xi-api-key`.
Scenes retain previous/next text context, input settings, audio, character alignment,
and ffprobe-measured duration. Returned character alignment becomes word cues; when
absent, captions use explicitly labeled proportional word estimates. The application
never presents estimates as forced alignment. Supported voice delivery keys are
validated and forwarded. Live capability depends on your voice/model/account access.

## Suno and imported music

No verified official Suno API contract or entitled account was supplied. The Suno
adapter is disabled with an explicit reason, and no unofficial endpoints are used.
To enable it in a future adapter, supply official developer documentation, an account
with API entitlement, supported authentication/task/result/cancel contracts, limits,
and reliable cost information. Until then, export/download your authorized music
from Suno and import it through Media, then add it to the music track.

[ElevenLabs Music](https://elevenlabs.io/docs/api-reference/music/compose) has a documented
API, but the optional live adapter is deferred; mock music and file import are fully
available. This avoids adding another paid integration without account/cost validation.

## Planner gateway

`LocalScriptPlanner` is deterministic and requires no credentials. `HttpScriptPlanner`
is an integration boundary for an operator-controlled LLM gateway. Set `PLANNER_URL`
on the API service and call `POST /api/projects/{id}/plan?planner=gateway`.
Its explicit application contract is POST JSON `{script, settings, schema}` and a
response matching `Storyboard.model_json_schema()`. This is not claimed to be any
vendor's native API. The gateway handles its model and credentials server-side.
Treat script strings as data; validate the returned schema and retain scene/shot IDs.
Do not connect a paid gateway without separately authorizing and enforcing its budget.

## Local Ollama planning

An additional concrete LLM adapter uses the documented
[Ollama chat API](https://docs.ollama.com/api/chat) with
[schema-constrained output](https://docs.ollama.com/capabilities/structured-outputs).
Run Ollama on a workstation/private server with a locally installed model. Set
`OLLAMA_URL=http://host.docker.internal:11434` (or your private service address) and
`OLLAMA_MODEL` to its installed model name, then recreate the API container.
The server must be reachable from Docker; a host service listening only on its own
loopback may need a private-network bind and firewall rules. Public/cloud endpoints
and cloud model tags are refused. No model download or paid cloud call is automatic.

The Script planner selector enables Local Ollama once those settings exist. Planning
uses `/api/chat`, `stream:false`, temperature 0, and the Pydantic storyboard JSON
schema. Narration is treated as data, output is validated, and server-generated IDs
are assigned once then retained through edits. Provider/model output quality still
requires storyboard review. No Ollama model was installed or exercised live during
this implementation; its HTTP contract is tested with deterministic fixtures.
