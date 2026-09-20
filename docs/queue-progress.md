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
