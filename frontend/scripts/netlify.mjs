import fs from 'node:fs/promises';

// Public backend ORIGIN only. No credential-bearing URL is accepted or printed.
let url;
try { url = new URL(process.env.API_PROXY_TARGET || ''); } catch { throw new Error('Set API_PROXY_TARGET to the public HTTPS Render web-service origin in Netlify. It is not a database URL.'); }
if (url.protocol !== 'https:' || !url.hostname.endsWith('.onrender.com') || url.username || url.password || url.search || url.hash || url.port || url.pathname !== '/') {
  throw new Error('API_PROXY_TARGET must be a public HTTPS *.onrender.com origin, with no credentials, port, path, query or fragment.');
}
await fs.writeFile('dist/_redirects', `/api/* ${url.origin}/api/:splat 200!\n/* /index.html 200\n`);
console.log('Generated same-origin API proxy before the SPA fallback. No secret values printed.');