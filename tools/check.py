"""Run a LOCAL check, retaining every failed attempt as a new diagnostic."""
import datetime
import pathlib
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parents[1]
label, *command = sys.argv[1:]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
stamp = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30))).strftime('%Y%m%d-%H%M%S-%f')
folder = root / ('evidence' if result.returncode == 0 else 'bugs')
folder.mkdir(exist_ok=True)
path = folder / f'{stamp}-{label}.txt'
path.write_text(f'LOCAL CHECK: {label}\nAsia/Kolkata: {stamp}\nExit code: {result.returncode}\n\n{result.stdout}')
print(result.stdout)
print(f'Evidence retained: {path.relative_to(root)}')
sys.exit(result.returncode)
