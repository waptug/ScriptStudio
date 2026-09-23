# Automatic native render resources

The native Windows worker reserves host resources before starting queued local
model generation, previews or final exports. One reservation spans concurrent
jobs and retry waits. A Windows named mutex serializes reservations across
native workspaces so they cannot overwrite each other's power-plan snapshots. It ends once the relevant queue is terminal and running
worker calls have drained, including failures and cancellations. Remote paid-only
and mock-only generation do not start a reservation. Existing local-model GPU
and Ollama coordination continues to manage model memory separately.

The native launcher sets `SCRIPTSTUDIO_RESOURCE_DIR` to its active workspace.
On first startup it creates `resource-optimization.json` there:

```json
{
  "enabled": true,
  "containers": [],
  "wsl_distribution": "Ubuntu",
  "high_performance": true,
  "above_normal_priority": true
}
```

Add exact Docker container names to `containers` to pause those background
workloads during rendering. Restart the app after changing configuration.
For example, `"containers": ["minecraft-vanilla", "aiagentswarm-manager-1"]`.
Only selected containers that were running and unpaused are reserved. Pausing
preserves their process memory and stops their CPU execution; it does not free
RAM. Do not include databases, networking or other services ScriptStudio needs.
The deployment configuration is machine-specific and is not embedded in builds.

On Windows the session selects the High Performance power plan and raises the
native supervisor priority to AboveNormal. It restores the exact original plan
and priority, using the process creation time to avoid touching a reused PID.
Already stopped or paused containers stay as they were. Recovery uses container
IDs, so a replacement with the same name is never resumed accidentally.

`resource-state.json` records pending restoration actions and errors. Changes
are journaled before execution. A separate guardian restores resources when the
worker closes its pipe, even if the native supervisor crashes. If the launcher
process container or Windows itself terminates the guardian too, restoration
runs on the next app startup. Failed restoration
is retried every five seconds; startup also recovers an unfinished journal before
new work. Normal shutdown drains active work first. If optimization preparation
fails, jobs remain queued and the runtime log records the error; partial host
changes are rolled back. Preserve the journal until recovery is complete.

The feature is wired into the native worker. Container-based Celery installations
do not automatically control host processes or Docker; they retain their existing
resource behavior. No Docker socket is mounted into the app.

Validation covers reservation idempotency, previously paused containers, partial
mutation rollback, durable recovery retries, failed render completion, and native
worker integration. The optional `RESOURCE_TEST_CONTAINER` test runs a real
native export against an isolated container. `backend/tools/resource_crash_smoke.py`
checks restoration after forcefully terminating the owner process.
