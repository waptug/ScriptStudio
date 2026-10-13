"""Self-contained Windows supervisor. No Docker, WSL, Redis or installed Python."""
import argparse
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time


def publish_ready(path, record):
    """Publish a complete readiness record; Windows readers never see a writer lock."""
    temporary = path.with_name(path.name + '.tmp')
    try:
        with temporary.open('w', encoding='utf-8') as stream:
            json.dump(record, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    data = Path(args.data).resolve()
    data.mkdir(parents=True, exist_ok=True)
    # Also enforce portable scratch/cache paths when the supervisor is started directly.
    temp = data / 'temp'
    temp.mkdir(exist_ok=True)
    profile = data / 'profile'
    local = profile / 'AppData/Local'
    roaming = profile / 'AppData/Roaming'
    local.mkdir(parents=True, exist_ok=True)
    roaming.mkdir(parents=True, exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp),
        USERPROFILE=str(profile), HOME=str(profile), LOCALAPPDATA=str(local), APPDATA=str(roaming),
        XDG_CACHE_HOME=str(data / 'cache'), PYTHONPYCACHEPREFIX=str(data / 'cache/python'))
    tempfile.tempdir = str(temp)
    sys.pycache_prefix = str(data / 'cache/python')
    # Windows denies a second supervisor access to this byte lock.
    sys.path.insert(0, str(root / 'backend'))
    from studio.platform_runtime import exclusive_file_lock
    if os.getenv('SCRIPTSTUDIO_SETUP_DISABLE_PAID') != '1':
        with exclusive_file_lock(data.parent / 'setup.lock'):
            pass  # Refuse launch while setup is backing up or changing components.
    with exclusive_file_lock(data / 'runtime.lock'):
        serve(root, data, args.port)


def serve(root, data, requested_port):
    logging.basicConfig(filename=data / 'runtime.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    config_path = data / 'runtime.json'
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding='utf-8'))
    else:
        config = {'password': secrets.token_hex(32), 'db_port': free_port(),
                  'port': requested_port or free_port()}
        config_path.write_text(json.dumps(config), encoding='utf-8')
    if requested_port and requested_port != config['port']:
        raise ValueError('This data directory uses a different saved HTTP port.')
    stop_path = data / 'stop.request'
    ready_path = data / 'ready.json'
    stop_path.unlink(missing_ok=True)
    ready_path.unlink(missing_ok=True)
    # Explicit bundled paths: never accidentally use media tools from another app.
    os.environ['PATH'] = os.pathsep.join(str(root / p) for p in
        ['ffmpeg/bin', 'speech', 'postgres/bin', 'python', 'msvc']) + os.pathsep + os.environ.get('SystemRoot', r'C:\Windows') + r'\System32'
    os.environ.update(DATABASE_URL=f"postgresql+psycopg://studio:{config['password']}@127.0.0.1:{config['db_port']}/scriptstudio",
        SCRIPTSTUDIO_RESOURCE_DIR=str(data), MEDIA_ROOT=str(data / 'media'), LOCAL_MODELS_ROOT=str(data.parent / 'local-models'), OPENSHOT_PYTHON=str(root / 'openshot/MediaHost.exe'),
        MOCK_FONT='DejaVuSans.ttf', ESPEAK_DATA_PATH=str(root / 'speech'),
        PYTHONUTF8='1', FFMPEG_FILTER_SCRIPT_OPTION='-/filter_complex', LIVE_GENERATION_ENABLED='false')
    for key in ('RUNWAY_API_KEY', 'ELEVENLABS_API_KEY'):
        os.environ.pop(key, None)
    os.chdir(root / 'backend')
    pg = root / 'postgres/bin'
    db = data / 'database'
    def pg_run(*command):
        with open(data / 'postgres-control.log', 'ab') as log:
            subprocess.run([str(pg / command[0]), *command[1:]], stdout=log,
                           stderr=log, check=True, timeout=120,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    if not (db / 'PG_VERSION').exists():
        password = data / 'init.password'
        try:
            password.write_text(config['password'], encoding='utf-8')
            pg_run('initdb.exe', '-D', str(db), '-U', 'studio',
                   '--pwfile='+str(password), '-A', 'scram-sha-256', '--encoding=UTF8', '--locale=C')
        finally:
            password.unlink(missing_ok=True)
    started = False
    stop = threading.Event()
    worker = None
    ollama = None
    ollama_url = None
    try:
        pg_run('pg_ctl.exe', 'start', '-D', str(db), '-l', str(data / 'postgres.log'),
               '-o', f"-h 127.0.0.1 -p {config['db_port']}", '-w')
        started = True
        import psycopg
        with psycopg.connect(host='127.0.0.1', port=config['db_port'], user='studio',
                password=config['password'], dbname='postgres', autocommit=True) as connection:
            if not connection.execute("SELECT 1 FROM pg_database WHERE datname='scriptstudio'").fetchone():
                connection.execute('CREATE DATABASE scriptstudio')
        from alembic.config import Config
        from alembic import command
        command.upgrade(Config(str(root / 'backend/alembic.ini')), 'head')
        if os.getenv('SCRIPTSTUDIO_SETUP_DISABLE_PAID') == '1':
            from studio.configuration import ConfigurationService, AdminUpdate
            ConfigurationService().save(AdminUpdate(paid_generation={'enabled': False}))
        llm_state = data.parent / 'local-llm/service.json'
        if llm_state.exists():
            try:
                service = json.loads(llm_state.read_text())
                if service.get('external_url') == 'http://127.0.0.1:11434':
                    ollama_url = service['external_url']
                elif service.get('executable'):
                    executable = Path(service['executable']).resolve()
                    if not executable.is_relative_to((data.parent / 'local-llm').resolve()):
                        raise ValueError('Private Ollama executable must be application-owned')
                    if 'ollama_port' not in config:
                        config['ollama_port'] = free_port()
                        config_path.write_text(json.dumps(config), encoding='utf-8')
                    ollama_url = f"http://127.0.0.1:{config['ollama_port']}"
                    environment = dict(os.environ, OLLAMA_HOST=f"127.0.0.1:{config['ollama_port']}",
                        OLLAMA_MODELS=service['models'], OLLAMA_NO_CLOUD='1', OLLAMA_KEEP_ALIVE='0')
                    ollama = subprocess.Popen([str(executable), 'serve'], env=environment,
                        stdout=open(data / 'ollama.log', 'ab'), stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                if ollama_url:
                    os.environ['OLLAMA_URL'] = ollama_url
                    if service.get('gemma'):
                        os.environ.update(OLLAMA_MODEL='gemma3:4b', SCRIPT_WRITER_MODEL='gemma3:4b')
            except (OSError, ValueError, KeyError):
                logging.exception('Optional Ollama startup failed; core remains available')
                ollama_url = None
        from studio.native_worker import serve as work
        from studio.api import app
        from starlette.staticfiles import StaticFiles
        import uvicorn
        app.mount('/', StaticFiles(directory=root / 'web', html=True), name='frontend')
        server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=config['port'], log_config=None, timeout_graceful_shutdown=5))
        worker = threading.Thread(target=work, args=(stop,), name='native-worker')
        worker.start()
        def monitor():
            while not server.started and not server.should_exit:
                time.sleep(.1)
            if server.started:
                try:
                    publish_ready(ready_path, {'url':f"http://127.0.0.1:{config['port']}",
                        'pid':os.getpid(), 'runtime':'native-windows', 'database':'PostgreSQL', 'ollama_url':ollama_url})
                except OSError:
                    logging.exception('Unable to publish runtime readiness')
                    server.should_exit = True
            while not server.should_exit:
                if stop_path.exists():
                    server.should_exit = True
                    break
                time.sleep(.25)
        threading.Thread(target=monitor, daemon=True).start()
        server.run()
    finally:
        ready_path.unlink(missing_ok=True)
        stop.set()
        if worker:
            worker.join()  # Drain active jobs before stopping their durable database.
        if started:
            pg_run('pg_ctl.exe', 'stop', '-D', str(db), '-m', 'fast', '-w')
        if ollama and ollama.poll() is None:
            ollama.terminate()
            try:
                ollama.wait(timeout=15)
            except subprocess.TimeoutExpired:
                ollama.kill()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Native startup/shutdown failed')
        raise
