"""Portable download names shared by an export's artifacts."""
from datetime import datetime, timezone
import re
import unicodedata

from .db import Project


def export_filename(session, job, extension):
    name = job.inputs.get('project_name')
    if name is None:  # Exports created before project names were captured.
        project = session.get(Project, job.project_id)
        name = project.name if project else 'Project'
    name = unicodedata.normalize('NFC', name)
    name = ''.join('_' if unicodedata.category(c).startswith('C') else c for c in name)
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', ' ', name).strip(' .')[:80].rstrip(' .') or 'Project'
    # Keep even multibyte names within common filesystem filename limits.
    name = name.encode('utf-8')[:160].decode('utf-8', errors='ignore').rstrip(' .')
    stamp = datetime.fromtimestamp(job.created, timezone.utc).strftime('%Y-%m-%d_%H-%M-%SZ')
    return f'{name}_{stamp}.{extension}'
