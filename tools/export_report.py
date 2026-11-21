from pathlib import Path
from markdown_it import MarkdownIt

root = Path(__file__).resolve().parents[1]
markdown = (root / 'FINAL_REPORT.md').read_text()
content = MarkdownIt('commonmark', {'html': False}).enable('table').render(markdown)
css = '''
@page { size: A4; margin: 18mm 16mm 20mm; }
body { font: 10.5px/1.65 -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color:#1c2c26; }
h1 { font-size:27px; line-height:1.2; letter-spacing:-.8px; color:#126a5c; margin:0 0 20px; }
h2 { font-size:19px; margin-top:28px; padding-top:14px; border-top:2px solid #126a5c; break-after:avoid; }
h3 { font-size:13px; margin-top:22px; break-after:avoid; }
p { orphans:3; widows:3; margin:10px 0; }
a { color:#126a5c; text-decoration:underline; overflow-wrap:anywhere; }
code { font-size:9px; background:#eff4ee; padding:1px 3px; overflow-wrap:anywhere; }
table { border-collapse:collapse; width:100%; font-size:8.5px; margin:15px 0; }
th,td { border:1px solid #dce5dd; padding:7px; text-align:left; vertical-align:top; }
th { background:#edf4ec; }
tr { break-inside:avoid; }
img { display:block; width:100%; height:315px; object-fit:contain; margin:20px auto 7px; border:1px solid #dce5dd; border-radius:5px; }
p:has(img) { break-inside:avoid; margin:24px 0; }
em { color:#526158; font-size:9px; }
'''
target = root / 'evidence/final-report.html'
target.write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><base href="../"><title>RecruitBoard final report</title><style>{css}</style></head><body>{content}</body></html>')
print('Generated evidence/final-report.html from the actual Markdown report.')