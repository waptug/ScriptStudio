# Queue phase progress

Every production queue and export job shows its applicable phases in sequence:
gray Queued, blue Prepare/Load model, purple Generate/Render, cyan Save/Encode/
Download, amber Check, and green Ready. Completed phases keep their colors and
checkmarks; the active phase is outlined; remaining phases are dimmed. Labels and
markers supplement color. Segments represent sequence, not time or an overall ETA.

The UI works with older backends using existing job states and generation steps.
Unknown percentages use indeterminate activity. Enhanced backends can supply
`result.queue_progress` for finer phases, loading counters and activity times.
Elapsed time and process contact do not prove measured progress. Connection loss
stops animation and shows reconnecting. Failed, canceled and uncertain jobs retain
known completed phases; old failed jobs do not invent history.

A UI-only update copies new hashed web assets and atomically switches index.html,
retaining old assets for open tabs. It does not restart the backend or model
processes. Open the updated UI in a new tab rather than replacing unsaved edits.
Do not replace the executable or deployed backend while any jobs are queued or
active. Backend progress reporting must wait for an idle-queue deployment.

## Reporting contract

`result.queue_progress` supplies `phases`, `completed`, `phase`, nullable
`fraction`, `detail`, `phase_started_at`, `last_activity_at`, and optional
`last_contact_at`. It is additive; older clients retain the existing `state`,
`progress`, and generation `steps` fields. The existing event stream carries it.
Progress metadata survives provider result replacement and safe retrieval retries;
new local attempts reset it. Terminal errors retain the last known phase.

Wan loading details read at most the last 32 KiB of its existing log and expose
only recognized component/checkpoint counts, never raw log text or URLs. A count
belongs to that subtask, not an overall loading percentage. Local subprocess
contact is recorded separately from changed counters or phase activity.

Rendering reports frame creation followed by audio/video encoding and final file
packaging. Local media reports output writing separately from generation. Only
successful asset ingestion marks the job Ready. None of these display fields
changes scheduling, cancellation, GPU reservations, costs or submission safety.

## Completed clips

Ready audio/video jobs expose **Preview clip** and **Add to timeline**. Preview
plays the original asset in the main preview window, with its own playback clock;
it does not change the timeline insertion point. **Return to timeline preview**
restores the project preview. Add inserts the full clip at the timeline playhead
on video, narration, music or sound-effects track as appropriate, using the
existing revision-checked, undoable timeline API. Existing items are preserved.
Clips already placed show **On timeline** to avoid adding duplicate copies.
Normal automatic placeholder filling remains controlled by the existing
**Fill eligible placeholders automatically** setting; locked or replaced takes
are not overwritten. Missing/unready assets do not show clip actions.
