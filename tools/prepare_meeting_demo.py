"""Freeze a meeting-demo release from the working tree; never changes containers or DBs.

Private runtime environment is recovered from the existing demo containers and
written outside the repository/build contexts. No credentials are printed.
"""
import argparse
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYTHON_BASE = 'python:3.10-slim@sha256:6ff506466f8b1e981719b468cc0023b8ef000b983cdec0eafe119d01f379e31d'
NODE_BASE = 'node:20-alpine@sha256:fb4cd12c85ee03686f6af5362a0b0d56d50c58a04632e6c0fb8363f609372293'
EXCLUDED = {
    'backend/app/domain/trivial_movement.py',
    'backend/app/models/trivial_board.py',
    'backend/app/models/trivial_content.py',
    'backend/app/schemas/trivial_persistence.py',
    'backend/app/services/trivial_content.py',
    'backend/app/services/trivial_persistence.py',
}
FRONT_ROOT = {'package.json', 'package-lock.json', 'next.config.ts', 'next.config.js',
              'next.config.mjs', 'tsconfig.json', 'postcss.config.mjs', 'postcss.config.js',
              'next-env.d.ts', 'eslint.config.mjs'}


def command(*args):
    return subprocess.check_output(args, cwd=ROOT).decode('utf-8').strip()


def environment(container):
    info = json.loads(command('docker', 'inspect', container))[0]
    if info['Mounts']:
        raise RuntimeError('Unexpected mounts on demo application container')
    return dict(value.split('=', 1) for value in info['Config']['Env'] if '=' in value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', required=True, type=pathlib.Path)
    parser.add_argument('--frontend-container', default='biogamed_meeting_demo-frontend-1')
    parser.add_argument('--backend-container', default='biogamed_meeting_demo-backend-1')
    args = parser.parse_args()
    output = args.output_root.resolve()
    if output == ROOT or ROOT in output.parents:
        raise RuntimeError('Release and private runtime files must be outside the repository')
    tracked = command('git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')
    sources = {}
    for name in tracked:
        p = pathlib.PurePosixPath(name)
        if name in EXCLUDED or not (ROOT / name).is_file():
            continue
        include = name.startswith('backend/app/') or name in {'backend/requirements.txt', 'backend/requirements.lock.txt'}
        include |= name.startswith(('frontend/src/', 'frontend/public/'))
        include |= len(p.parts) == 2 and p.parts[0] == 'frontend' and p.parts[1] in FRONT_ROOT
        if not include:
            continue
        if any(part.startswith('.env') or part in {'node_modules', '__pycache__', '.next'} for part in p.parts):
            raise RuntimeError('Unexpected private/generated source path')
        data = (ROOT / name).read_bytes()
        if p.suffix in {'.py', '.ts', '.tsx', '.js', '.mjs', '.json', '.css', '.txt', '.svg'}:
            data = data.replace(b'\r\n', b'\n')
        if name == 'backend/app/models/__init__.py':
            lines = data.decode('utf-8').splitlines(keepends=True)
            removed = [line for line in lines if line.startswith(('from app.models.trivial_board import ', 'from app.models.trivial_content import '))]
            if len(removed) != 2:
                raise RuntimeError('Review integrated-profile model registrations before rebuilding')
            data = ''.join(line for line in lines if line not in removed).encode()
        sources[name] = data
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(sources.items())}
    digest = hashlib.sha256(json.dumps({'files': hashes, 'python_base': PYTHON_BASE, 'node_base': NODE_BASE, 'profile_version': 1}, sort_keys=True).encode()).hexdigest()
    revision = command('git', 'rev-parse', 'HEAD')
    release = 'meeting-' + revision[:7] + '-' + digest[:12]
    destination = output / release
    if destination.exists():
        raise RuntimeError('Release already exists; rebuild its saved Compose instead of overwriting it')
    back = environment(args.backend_container)
    front = environment(args.frontend_container)
    if not back.get('SECRET_KEY', '').strip() or back['SECRET_KEY'].strip() == 'dev-only-change-this-secret-key-before-production':
        raise RuntimeError('Demo needs an existing valid explicit JWT key')
    # The database must remain the existing demo service, never a host or habitual DB.
    from urllib.parse import urlsplit
    db = urlsplit(back['DATABASE_URL'])
    if db.hostname != 'db' or db.path != '/biogamed_demo':
        raise RuntimeError('Unexpected demo database destination')
    for name, data in sources.items():
        target = destination / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    runtime = destination / 'runtime'
    runtime.mkdir()
    selected = {key: value for key, value in back.items() if key in {'DATABASE_URL', 'SECRET_KEY', 'BIOGAMED_CORS_ORIGIN'} or key.startswith('AUTH_')}
    # Compose env_file raw mode preserves literal $, #, quotes and backslashes.
    if any('\n' in value or '\r' in value for value in selected.values()):
        raise RuntimeError('Multiline runtime values require explicit review')
    (runtime / 'backend.env').write_text(''.join(key + '=' + value + '\n' for key, value in selected.items()), encoding='utf-8')
    public = {key: value for key, value in front.items() if key.startswith('NEXT_PUBLIC_')}
    if public.get('NEXT_PUBLIC_API_BASE_URL') != 'http://localhost:18004':
        raise RuntimeError('Unexpected demo public API URL')
    (destination / 'source/backend/Dockerfile').write_text('FROM ' + PYTHON_BASE + '\nWORKDIR /app\nCOPY requirements.txt requirements.lock.txt ./\nRUN pip install --no-cache-dir -r requirements.txt -c requirements.lock.txt\nCOPY app ./app\nCMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]\n')
    frontend_docker = 'FROM ' + NODE_BASE + '\nWORKDIR /app\nCOPY package*.json ./\nRUN npm ci\nCOPY . .\n'
    frontend_docker += ''.join('ARG ' + key + '\nENV ' + key + '=${' + key + '}\n' for key in public)
    frontend_docker += 'ENV NEXT_TELEMETRY_DISABLED=1\nRUN npm run build\nEXPOSE 3000\nCMD ["npm", "run", "start", "--", "--hostname", "0.0.0.0", "--port", "3000"]\n'
    (destination / 'source/frontend/Dockerfile').write_text(frontend_docker)
    labels = {'org.opencontainers.image.revision': revision, 'biogamed.release': release, 'biogamed.profile': 'integrated-meeting-no-board-engine'}
    services = {}
    for area, port in [('backend', 18004), ('frontend', 13004)]:
        service = {'image': 'biogamed-meeting-' + area + ':' + release,
                   'build': {'context': './source/' + area, 'labels': labels},
                   'ports': ['127.0.0.1:' + str(port) + (':8000' if area == 'backend' else ':3000')],
                   'restart': 'unless-stopped', 'labels': labels}
        if area == 'backend':
            service['env_file'] = [{'path': './runtime/backend.env', 'format': 'raw'}]
        else:
            service['build']['args'] = public
        services[area] = service
    compose = {'services': services, 'networks': {'default': {'external': True, 'name': 'biogamed_docente_demo_default'}}}
    (destination / 'compose.json').write_text(json.dumps(compose, indent=2))
    manifest = {'release': release, 'revision': revision, 'source_sha256': digest, 'files': hashes,
                'working_tree_status': command('git', 'status', '--short'),
                'excluded_internal_files': sorted(EXCLUDED),
                'transformation': 'Remove only the two excluded internal Trivial model registrations from models/__init__.py.',
                'database_revision_required': 'e64f73085196', 'automatic_migrations': False, 'base_images': [PYTHON_BASE, NODE_BASE]}
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps({'release': release, 'directory': str(destination), 'source_files': len(sources), 'private_values_printed': False}))


if __name__ == '__main__':
    main()
