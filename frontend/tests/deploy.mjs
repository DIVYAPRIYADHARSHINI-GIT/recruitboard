import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
const root = path.resolve('..');
const temp = path.join(root, '.test-data', 'proxy-config');
await fs.mkdir(path.join(temp, 'dist'), { recursive: true });
const script = path.resolve('scripts/netlify.mjs');
let count = 0;
for (const target of ['', 'http://public.onrender.com', 'https://example.invalid', 'https://public.onrender.com/private', 'https://public.onrender.com?query=1']) {
  const result = spawnSync(process.execPath, [script], { cwd: temp, env: { ...process.env, API_PROXY_TARGET: target }, encoding: 'utf8' });
  assert.notEqual(result.status, 0); count++;
}
const valid = spawnSync(process.execPath, [script], { cwd: temp, env: { ...process.env, API_PROXY_TARGET: 'https://recruitboard-example.onrender.com' }, encoding: 'utf8' });
assert.equal(valid.status, 0); count++;
const redirects = await fs.readFile(path.join(temp, 'dist/_redirects'), 'utf8');
assert.equal(redirects, '/api/* https://recruitboard-example.onrender.com/api/:splat 200!\n/* /index.html 200\n'); count++;
assert.equal((redirects.match(/200!/g) || []).length, 1); count++;
console.log(`${count} deployment-configuration checks passed. No network requests or real hosting resources used.`);
