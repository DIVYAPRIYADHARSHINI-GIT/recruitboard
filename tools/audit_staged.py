"""Conservative staged-file guard; never prints matched secret values."""
import pathlib
import re
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'diff', '--cached', '--name-only', '-z'], cwd=root).decode().split('\0')
problems = []
maximum = 5 * 1024 * 1024
secret_patterns = [
    re.compile(rb'gh[pousr]_[A-Za-z0-9]{20,}'),
    re.compile(rb'github_pat_[A-Za-z0-9_]{20,}'),
    re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    re.compile(rb'postgres(?:ql)?(?:\+psycopg)?://[^\s\"\'<>]+:[^\s\"\'<>]+@'),
    re.compile(rb'(?:npg_|nfp_|rnd_)[A-Za-z0-9]{20,}'),
]
count = total = 0
for name in filter(None, paths):
    parts = pathlib.PurePosixPath(name).parts
    if any(part.startswith('.env') for part in parts):
        problems.append(f'Environment file staged: {name}')
        continue
    if any(part in {'.venv', 'node_modules', '.cache', '.browser', '.test-data'} for part in parts) or name.endswith(('.db', '.sqlite', '.sqlite3')):
        problems.append(f'Private/runtime artifact staged: {name}')
        continue
    blob = subprocess.check_output(['git', 'show', ':'+name], cwd=root)
    count += 1
    total += len(blob)
    if len(blob) > maximum:
        problems.append(f'File exceeds 5 MB review threshold: {name}')
    if any(pattern.search(blob) for pattern in secret_patterns):
        problems.append(f'Potential credential pattern in {name}; value withheld')
if problems:
    print('\n'.join(problems))
    sys.exit(1)
print(f'Staged audit passed: {count} files, {total:,} bytes; no environment/private runtime artifacts, file over 5 MB or recognized credential pattern.')
print('This heuristic supplements manual review; it is not a guarantee that every possible secret is detectable.')