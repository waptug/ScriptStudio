# Introducing ScriptStudio: local AI demo

The dashboard offers **Create 60-second ScriptStudio demo · local AI** beside
its explicitly labeled mock demo. One click creates a separate project and queues
Kokoro narration, followed by twelve Wan shots and a 60-second ACE-Step
instrumental. All three installed models must be Ready. No mock fallback or paid
provider is used. The prompt is “Introducing ScriptStudio and what it does.”

The built-in narration and storyboard explain scripts, visual planning, local
models, queue progress, previews, timeline editing, clip naming, captions and
export. Each Wan output provides five seconds of timeline coverage. Twelve shots
make exactly 1,440 frames at 24 fps. Narration is neither accelerated nor cut; if
it unexpectedly exceeds 60 seconds assembly stops with an actionable error.
Music spans the full minute. Generation may take several hours on a consumer GPU.

The ordinary PostgreSQL job queue, model readiness checks, GPU coordination and
placeholder rules apply. Reconciliation is restart safe: it creates the timeline
and downstream jobs once, then automatically queues one captioned final export
when all generation jobs are Ready. Failed jobs require the existing Retry
control. Missing or user-replaced placeholders are never recreated for export.
Disabling automatic placement also disables the automatic export. Manual edits
are honored, including duration changes; the untouched preset is exactly 60s.

Generated clips can be previewed, renamed and added through the existing queue
controls. The finished render appears with the other completed jobs and exports.
