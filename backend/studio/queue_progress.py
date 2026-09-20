"""Display-only job phases; scheduling and retry state remain authoritative."""
from copy import deepcopy
import re
import time

PHASES = ('queued', 'prepare', 'generate', 'transfer', 'validate', 'ready')
LOCAL_MODELS = ('wan', 'kokoro', 'ace_step', 'stable_audio')
UNSET = object()


def sequence(job):
    return ['queued', 'generate', 'validate', 'ready'] if job.provider == 'mock' else list(PHASES)


def phase_for(job):
    state = job.state
    if state in ('queued', 'waiting_for_gpu'): return 'queued'
    if state == 'loading': return 'prepare'
    if state == 'submitting': return 'generate' if job.provider == 'mock' else 'prepare'
    if state in ('submitted', 'generating'): return 'generate'
    if state == 'downloading': return 'validate' if job.provider == 'mock' else 'transfer'
    if state == 'validating': return 'validate'
    if state == 'ready': return 'ready'


def record(job, phase=None, fraction=UNSET, detail=None, contact=False, reset=False):
    """Merge progress only; never change job state, leases, costs or provider IDs."""
    now = time.time()
    reset = reset or job.state == 'waiting_for_gpu'
    phases = sequence(job)
    old = {} if reset else deepcopy((job.result or {}).get('queue_progress') or {})
    target = phase or phase_for(job)
    if target not in phases: return
    previous = old.get('phase')
    # Local provider.submit returns only after creation; submitted/downloading
    # bookkeeping must not visually rewind its already-validated output.
    if previous in phases and phases.index(target) < phases.index(previous) and not reset:
        return
    changed = target != previous
    value = None if fraction is UNSET and changed else old.get('fraction') if fraction is UNSET else fraction
    if value is not None: value = max(0.0, min(1.0, float(value)))
    text = detail if detail is not None else '' if changed else old.get('detail', '')
    activity = changed or value != old.get('fraction') or text != old.get('detail', '')
    current = {**old, 'phases': phases, 'phase': target,
               'completed': phases if job.state == 'ready' else phases[:phases.index(target)],
               'fraction': 1 if job.state == 'ready' else value, 'detail': text,
               'phase_started_at': now if changed else old.get('phase_started_at', now),
               'last_activity_at': now if activity else old.get('last_activity_at', now)}
    if contact or activity: current['last_contact_at'] = now
    job.result = {**(job.result or {}), 'queue_progress': current}


def apply_changes(job, changes, **progress):
    existing = deepcopy((job.result or {}).get('queue_progress'))
    for key, value in changes.items():
        setattr(job, key, value)
    if existing:
        job.result = {**(job.result or {}), 'queue_progress': existing}
    record(job, **progress)


# Read only fixed, public counters. Never forward arbitrary log lines, paths,
# prompts, URLs or credentials to the API. Re-read a bounded tail to tolerate
# carriage-return progress lines and partial writes without accumulating memory.
COUNTER = re.compile(r'(Loading pipeline components|Loading checkpoint shards).*?\|\s*(\d+)/(\d+)(?=\s|\[|$)')


def loading_detail(log_path):
    try:
        with log_path.open('rb') as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell()-32768))
            tail = stream.read(32768).decode('utf-8', errors='replace')
    except OSError:
        return None
    matches = list(COUNTER.finditer(tail))
    if not matches: return None
    name, current, total = matches[-1].groups()
    current, total = int(current), int(total)
    if not 0 <= current <= total or not 0 < total <= 100000: return None
    label = 'Pipeline components' if name == 'Loading pipeline components' else 'Checkpoint shards'
    return f'{label} {current} / {total}'
