"""Refresh the About inventory from lockfiles and the running Compose images.

Run after installing frontend dependencies and rebuilding/starting Compose.
Only package metadata and copyright/license files are read from containers.
"""
import io
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'frontend/public/credits'


def compose(service, *command, input=None):
    return subprocess.run(['docker', 'compose', 'exec', '-T', service, *command],
                          cwd=ROOT, input=input, capture_output=True, check=True).stdout


def inventory():
    records = []
    packages = json.loads((ROOT / 'frontend/package-lock.json').read_text())['packages']
    for path, package in packages.items():
        if not path:
            continue
        name = path.split('node_modules/')[-1]
        notices = []
        directory = ROOT / 'frontend' / path
        if directory.is_dir():
            installed = json.loads((directory/'package.json').read_text())
            if installed['version'] != package['version']:
                raise RuntimeError(f'Run npm ci: installed {name} differs from lockfile')
            for file in sorted(directory.iterdir()):
                if file.is_file() and re.match(r'(?i)^(licen[cs]e|copying|notice)(\.|$)', file.name):
                    notices.append(file.read_text(errors='replace'))
        records.append(dict(name=name, version=package['version'], group='JavaScript',
                            license=package['license'], url=f'https://www.npmjs.com/package/{name}/v/{package["version"]}',
                            role='Build/test dependency' if package.get('dev') else 'Browser runtime',
                            evidence='frontend/package-lock.json; optional platform packages included',
                            notice='\n\n'.join(notices)))
    python_script = '''
import importlib.metadata as metadata
import json
rows=[]
for dist in metadata.distributions():
    m=dist.metadata
    notices=[]
    for file in dist.files or []:
        if ('.dist-info/' in str(file) and any(part.lower().startswith(('license','copying','notice')) for part in file.parts)):
            path=dist.locate_file(file)
            if path.is_file(): notices.append(path.read_text(errors='replace'))
    license=m.get('License-Expression') or m.get('License') or '; '.join(c.split(' :: ')[-1] for c in m.get_all('Classifier',[]) if c.startswith('License'))
    rows.append(dict(name=m['Name'],version=dist.version,group='Python',license=license or 'See upstream license files',
                     url='https://pypi.org/project/'+m['Name']+'/'+dist.version+'/',role='Backend / test tooling',
                     evidence='Installed Python distribution metadata in api image',notice='\\n\\n'.join(notices)))
print(json.dumps(rows))
'''
    python_rows = json.loads(compose('api', 'python', '-', input=python_script.encode()))
    installed = {re.sub(r'[-_.]+', '-', row['name']).lower():row['version'] for row in python_rows}
    for line in (ROOT / 'backend/requirements.lock').read_text().splitlines():
        name, version = line.split('==')
        if installed.get(re.sub(r'[-_.]+', '-', name).lower()) != version:
            raise RuntimeError(f'Rebuild backend image: installed {name} differs from lockfile')
    records.extend(python_rows)
    for service in ('api', 'db'):
        # Dereference Debian documentation symlinks so shared notices are retained.
        paths = compose(service, 'find', '-L', '/usr/share/doc', '-name', 'copyright', '-type', 'f', '-print0')
        paths += compose(service, 'find', '-L', '/usr/share/common-licenses', '-type', 'f', '-print0')
        paths += b'/var/lib/dpkg/status\0'
        archive = compose(service, 'tar', '-chf', '-', '--null', '-T', '-', input=paths)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            documents = {m.name:tar.extractfile(m).read().decode(errors='replace') for m in tar.getmembers()
                         if (m.isfile() or m.islnk()) and (m.name.endswith('/copyright') or m.name.startswith('usr/share/common-licenses/') or m.name=='var/lib/dpkg/status')}
        for paragraph in documents['var/lib/dpkg/status'].split('\n\n'):
            fields = dict(re.findall(r'^([\w-]+): (.*)$', paragraph, re.M))
            if fields.get('Status') != 'install ok installed':
                continue
            name = fields['Package']
            notice = documents.get(f'usr/share/doc/{name}/copyright', '')
            tags = sorted(set(re.findall(r'^License: (.+)$', notice, re.M)))
            records.append(dict(name=name, version=fields['Version'], group=f'Debian · {service}',
                                license='; '.join(tags) if tags else 'See package copyright notice',
                                url=fields.get('Homepage', 'https://packages.debian.org/'+name), role='Container system dependency',
                                evidence=f'{service} image: /usr/share/doc/{name}/copyright', notice=notice))
        for path, notice in documents.items():
            if path.startswith('usr/share/common-licenses/'):
                records.append(dict(name=path.rsplit('/',1)[-1], version='Debian common text', group=f'License texts · {service}',
                                    license=path.rsplit('/',1)[-1], url='https://www.debian.org/legal/licenses/',
                                    role='Referenced full license text', evidence='/'+path, notice=notice))
    for service in ('web', 'redis'):
        database = compose(service, 'cat', '/lib/apk/db/installed').decode()
        for paragraph in database.split('\n\n'):
            fields = dict(re.findall(r'^([A-Za-z]):(.*)$', paragraph, re.M))
            if 'P' not in fields:
                continue
            records.append(dict(name=fields['P'], version=fields['V'], group=f'Alpine · {service}',
                                license=fields.get('L', 'See upstream notices'), url=fields.get('U','https://pkgs.alpinelinux.org/'),
                                role='Container system dependency', evidence=f'{service} image: /lib/apk/db/installed', notice=''))
    return records


if __name__ == '__main__':
    rows = inventory()
    # Source-built runtimes are not all represented by OS package managers.
    rows.extend([
        dict(name='Python',version='3.12.10',group='Foundation',license='PSF-2.0 and bundled notices',url='https://docs.python.org/3.12/license.html',role='Backend runtime'),
        dict(name='Node.js',version='22.15.0',group='Foundation',license='MIT and bundled notices',url='https://github.com/nodejs/node/blob/v22.15.0/LICENSE',role='Frontend build runtime'),
        dict(name='PostgreSQL',version='17.4',group='Foundation',license='PostgreSQL License',url='https://www.postgresql.org/about/licence/',role='Durable project and job database'),
        dict(name='Redis server',version='7.4.2',group='Foundation',license='RSALv2 OR SSPLv1 (source-available)',url='https://redis.io/legal/licenses/',role='Background job wakeups; separate from the MIT Python redis client'),
        dict(name='nginx',version='1.27.5',group='Foundation',license='BSD-2-Clause',url='https://nginx.org/LICENSE',role='Web server and API proxy'),
        dict(name='OpenShot Video Editor',version='2.6.1 (optional verification image)',group='Optional tools',license='GPL-3.0-or-later',url='https://github.com/OpenShot/openshot-qt/blob/v2.6.1/COPYING',role='Editable project handoff; desktop editor not bundled in the app'),
        dict(name='Ollama',version='External installation',group='Optional tools',license='MIT (software); model licenses vary',url='https://github.com/ollama/ollama/blob/main/LICENSE',role='Optional local script writing and planning; models are installed separately'),
        dict(name='Docker Engine / Compose',version='Host installation',group='Optional tools',license='Apache-2.0 (open-source engine and Compose)',url='https://github.com/docker/compose/blob/main/LICENSE',role='Container tooling; Docker Desktop has separate terms'),
    ])
    rows.sort(key=lambda r:(r['group'],r['name'].lower()))
    OUT.mkdir(parents=True, exist_ok=True)
    notices = {}
    for row in rows:
        if row.get('notice'):
            text = row['notice']
            key = hashlib.sha256(text.encode()).hexdigest()
            notices[key] = text
            row['notice'] = key
    payload = dict(schema=1, scope='Locked JavaScript dependencies (including optional platforms), installed Python distributions, Debian api/db and Alpine web/redis packages, plus foundation and optional tools. Host OS, Docker Desktop, external model weights, and proprietary services are outside the bundled inventory.', components=rows)
    (OUT/'components.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    (OUT/'notices.json').write_text(json.dumps(notices,ensure_ascii=False,indent=2)+'\n')
    for source, target in [('LICENSE','LICENSE.txt'),('NOTICE.md','NOTICE.txt')]:
        (OUT/target).write_bytes((ROOT/source).read_bytes())
    print(f'Wrote {len(rows)} component and license-text records to {OUT}')
