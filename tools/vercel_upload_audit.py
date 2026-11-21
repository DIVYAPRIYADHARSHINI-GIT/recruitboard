"""Dry deployment-file audit only. Never pull/read cloud environment values."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
result = subprocess.run(['vercel', 'deploy', '--dry', '--json', '--prod', '--project', 'recruitboard', '--scope', 'divya-6411', '--no-color'], cwd=root, capture_output=True, text=True)
if result.returncode:
    # No secret input is supplied; do not dump a possibly broad structured response.
    print('Vercel dry inspection failed. CLI diagnostic:')
    print(result.stderr[:4000])
    sys.exit(result.returncode)
data = json.loads(result.stdout)
print('Dry-result structure:', list(data.keys()) if isinstance(data, dict) else type(data).__name__)
files = data.get('files', []) if isinstance(data, dict) else data
names = []
if isinstance(files, dict):
    names = list(files)
elif isinstance(files, list):
    names = [item if isinstance(item, str) else item.get('path') or item.get('file') or item.get('name') for item in files]
names = [name for name in names if isinstance(name, str)]
if not names:
    print('No deployment filename list was recognized; upload has NOT been approved.')
    sys.exit(1)
problems = []
for name in names:
    parts = Path(name).parts
    if any(part.startswith('.env') or part.startswith('.venv') or part in {'.browser', '.cache', '.test-data', '.git', 'node_modules', 'screenshots', 'bugs', 'evidence'} for part in parts):
        problems.append(name)
    if name.endswith(('.db', '.sqlite', '.pdf', '.lock-db')):
        problems.append(name)
if problems:
    print('Forbidden upload filenames:', json.dumps(sorted(set(problems))))
    sys.exit(1)
summary = {'mode': 'dry; no deployment created', 'file_count': len(names), 'files': sorted(names), 'forbidden_files': 0}
(root / 'evidence/vercel-upload-audit.json').write_text(json.dumps(summary, indent=2))
print(f'Upload audit passed: {len(names)} source files; no environment files, local data, dependencies, reports or credentials included.')
print('No Vercel environment-pull or local-cloud-build command was run.')
