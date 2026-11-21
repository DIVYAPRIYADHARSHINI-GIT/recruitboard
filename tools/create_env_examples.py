"""Create ignored placeholder-only environment templates after cloning."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
templates = {
    'backend/.env.example': '# Documentation only. Export variables explicitly; no dotenv autoload.\nDATABASE_URL=sqlite:///./recruitboard.db\nAPP_ENV=development\nALLOWED_ORIGINS=http://localhost:5173,http://localhost:4173,http://127.0.0.1:4173\nSEED_DEMO=true\nDEMO_MODE=true\nCOOKIE_SECURE=false\nLOGIN_LIMIT=10\nWRITE_LIMIT=120\n',
    'frontend/.env.example': '# Never put secrets here.\nVITE_API_BASE=/api\n# Netlify build only: API_PROXY_TARGET is the public Render origin, not a secret.\n',
}
for name, content in templates.items():
    target = root / name
    if target.exists():
        print(f'Left existing template untouched: {name}')
    else:
        target.write_text(content)
        print(f'Created placeholder template: {name}')