# Known limitations

- Single-user local workstation application; no authentication, collaboration, cloud
  storage, multi-tenant scheduling, or SaaS billing. Do not expose it publicly as-is.
- Preview must be rebuilt after edits. It is a synchronized rendered proxy, not an
  immediate interactive GPU compositor. OpenShot's desktop handoff provides richer
  editing without rebuilding those tools in the browser.
- Runway and ElevenLabs are documented adapters, not live-tested integrations. Paid
  generation remains disabled until credentials, account capabilities, explicit
  authorization, and a defined project budget are supplied. Suno API is disabled;
  imported Suno music is supported. Optional ElevenLabs Music is deferred.
- Default planning is deterministic. Optional local Ollama planning needs a reachable
  server and an installed local model; the generic gateway needs its documented JSON contract.
  Prompt-to-script writing is a separate optional local-model workflow with explicit
  draft review. Scene planning additionally requires working structured-output support.
- Admin settings apply to supported adapters, not arbitrary providers. Credentials
  are encrypted locally; this is still a single-user app without an Admin login.
- Mock imagery is synthetic labeled footage; speech uses eSpeak and caption timings
  are proportional estimates, not exact speech recognition. Target duration is a
  planning guide; narration is never sped up or padded to pretend it hits a target.
- No synchronized character lip motion, advanced compositing, 3D effects, or automatic
  intelligent scene redesign. Supported transitions are cuts and alpha fades.
- Video source audio is not mixed automatically. Import separate audio on narration,
  music, or sound-effect tracks. Visual coverage normalization may increase disk usage.
- A five-minute project with many word-caption images can render slowly and produce a
  large OpenShot bundle. Source media and old renders are retained; disk cleanup is
  currently an operator responsibility after backup.
- OpenShot handoff is one-way. Titles/captions are image clips; source coverage is
  normalized; finished audio is a single baked mix. Originals and alternate takes are
  retained for richer desktop edits. Platform/version compatibility claims are limited
  to the exact engine/desktop tests recorded in `verification.md`.
- Estimated costs include pending/uncertain potentially charged requests. Provider
  account statements remain the authority for actual billing. Unknown submissions
  need operator reconciliation; Runway task-ID recovery cannot discover a lost ID
  automatically through an undocumented API.
