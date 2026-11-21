// Preserve a privacy-cropped copy of a USER-SUPPLIED image, not a fresh dashboard capture.
// No network navigation, account access, image generation or modification of error text.
import { chromium } from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';

const source = process.argv[2];
if (!source) throw new Error('Pass the user-supplied Render Events image path.');
const root = path.resolve('..');
const target = path.join(root, 'bugs/BUG-014-render-deployment-failed-user-supplied-detail.png');
await fs.mkdir(path.join(root, '.browser/tmp'), { recursive: true });
const bytes = await fs.readFile(source);
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
try {
  const context = await browser.newContext({ offline: true });
  const page = await context.newPage();
  const result = await page.evaluate(async base64 => {
    const image = new Image();
    image.src = `data:image/png;base64,${base64}`;
    await image.decode();
    // Remove unrelated workspace navigation/account controls while retaining the deployment events.
    const crop = {
      x: Math.floor(image.naturalWidth * 0.06),
      y: Math.floor(image.naturalHeight * 0.36),
      width: Math.floor(image.naturalWidth * 0.92),
      height: Math.floor(image.naturalHeight * 0.52)
    };
    const canvas = document.createElement('canvas');
    canvas.width = crop.width; canvas.height = crop.height;
    canvas.getContext('2d').drawImage(image, crop.x, crop.y, crop.width, crop.height, 0, 0, crop.width, crop.height);
    return { png: canvas.toDataURL('image/png').split(',')[1], crop, original: { width: image.naturalWidth, height: image.naturalHeight } };
  }, bytes.toString('base64'));
  await fs.writeFile(target, Buffer.from(result.png, 'base64'), { flag: 'wx' });
  await fs.writeFile(target.replace('.png', '.json'), JSON.stringify({ provenance: 'User-supplied Render Events screenshot; cropped locally to omit unrelated workspace/account navigation. Not an agent-captured live dashboard.', originalDimensions: result.original, crop: result.crop, networkRequests: 0 }, null, 2), { flag: 'wx' });
  console.log('Saved bugs/BUG-014-render-deployment-failed-user-supplied-detail.png; first crop retained unchanged.');
  console.log('Provenance: user-supplied screenshot, privacy-cropped only. No network requests.');
  console.log('Original dimensions:', result.original.width, 'x', result.original.height);
  console.log('Crop dimensions:', result.crop.width, 'x', result.crop.height);
} finally { await browser.close(); }
