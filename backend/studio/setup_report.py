"""Read local versioned setup evidence without exposing inventory to public APIs."""
import json
import os
from pathlib import Path


def evidence(filename):
    resource = os.getenv('SCRIPTSTUDIO_RESOURCE_DIR')
    if not resource:
        return None
    # Supervisor sets the application's data directory; callers cannot choose paths.
    file = Path(resource).parent / filename
    try:
        if file.stat().st_size > 16 * 1024 * 1024:
            return None
        report = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(report, dict) or report.get('contract_version') != 1:
            return None
        return report
    except (OSError, ValueError):
        return None


def model_evidence(name, saved):
    acceptance = evidence('setup-acceptance.json') or {}
    plan = acceptance.get('plan')
    components = plan.get('components', []) if isinstance(plan, dict) else []
    if not isinstance(components, list):
        components = []
    component = next((c for c in components if isinstance(c, dict) and c.get('id') == name), {})
    status = component.get('status', 'Unknown')
    reason = component.get('reason', 'Run the Windows setup hardware review; runtime verification is required')
    if saved.get('state') == 'ready':
        status, reason = 'Compatible', 'Installed runtime probe passed; generation verification is reported separately'
    elif saved.get('state') in ('failed', 'interrupted'):
        status, reason = 'Needs repair', saved.get('error') or 'Resume and verify the interrupted installation'
    return {
        'compatibility_status': status,
        'compatibility_reason': reason,
        'verification_status': 'runtime_verified' if saved.get('state') == 'ready' else 'not_verified',
        'generation_verification_status': saved.get('generation_verification_status', 'not_verified'),
    }
