# Admin models and credentials

Open **Admin** in the dashboard or project header. This is the existing local,
single-user installation; Admin is not an authenticated multi-user administration
system. Keep the web service bound to loopback. Remote access requires authentication,
authorization, and TLS in front of the whole application.

## Workflow configuration

- **Script writing:** choose a local Ollama model. The writer returns narration
  paragraphs with optional bracketed visual instructions, then validates that the
  output contains narration. It uses plain text because prose does not require a
  JSON grammar. Generated drafts require explicit acceptance into the editor.
- **Scene planning:** independently choose a local Ollama model supporting structured
  JSON output. The deterministic planner remains the default and requires no AI setup.
  A blank script-writing model falls back to the configured planning model.
- **Video:** Runway model name and estimated USD per second. The existing adapter
  targets the image-to-video API with the documented gen4.5 request contract; entering
  an arbitrary model name does not implement new provider capabilities.
- **Narration:** ElevenLabs model and estimated USD per character. Select the voice ID
  and provider in Project settings. Account access and endpoint compatibility still apply.
- **Music:** local synthesis or imported audio. Suno remains disabled pending verified
  official API access; no unsupported credential field pretends otherwise.

Set Ollama URL to a local/private address reachable from the API container, commonly
`http://host.docker.internal:11434`. **List installed models** performs a read-only
connectivity check and populates suggestions. Models are never downloaded automatically.
Cloud models and public Ollama addresses are refused. Requests time out after three
minutes; existing script/draft content is retained on errors.

Saved Admin values take precedence over environment defaults, including intentionally
blank values. Changes affect subsequent requests in both API and workers. Queued video
and narration requests already contain their model and do not switch when Admin changes.
Keys are read when a provider call is made; avoid changing provider accounts while jobs
are active. Saving credentials never changes `LIVE_GENERATION_ENABLED` or project budgets.

## Credential storage

Runway and ElevenLabs keys are encrypted with authenticated Fernet encryption before
being saved to PostgreSQL's `app_settings` table. The API returns only configured status
and whether the value comes from Admin or environment. Password fields are always blank
on load. Empty fields preserve existing keys; Clear saves an empty override, including
when a key remains in the server environment. No key is written to browser local storage.

The encryption key is generated once at `/data/.credentials/master.key` with mode 0600
inside a mode-0700 directory. API and worker containers share this persistent media
volume. Keep the matching database and media-volume backups together and secure: access
to both permits decryption. Encryption does not protect against a compromised host or
API process. Never delete/replace the master key to reset credentials. Restore it from
backup if missing; the application refuses to silently replace it when encrypted records
already exist. Environment keys remain supported but are not encrypted by this mechanism.

Admin endpoints reject cross-origin browser requests and non-JSON mutations; responses
are non-cacheable, validation failures do not echo secret inputs, and keys never appear
in project exports. These controls do not replace authentication for remote deployment.
