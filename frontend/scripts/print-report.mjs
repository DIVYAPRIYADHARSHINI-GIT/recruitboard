import { chromium } from 'playwright';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import fs from 'node:fs/promises';
const root = path.resolve('..');
await fs.mkdir(path.join(root, '.browser/tmp'), { recursive: true });
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true });
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.join(root, 'evidence/final-report.html')).href);
  await page.evaluate(async () => { await Promise.all([...document.images].map(image => image.decode())); });
  await page.pdf({ path: path.join(root, 'FINAL_REPORT.pdf'), format: 'A4', printBackground: true, displayHeaderFooter: true, headerTemplate: '<span></span>', footerTemplate: '<div style="font-size:8px;color:#526158;width:100%;margin:0 16mm;display:flex;justify-content:space-between"><span>RecruitBoard · observed evidence, not assumed results</span><span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>' });
  console.log('Exported FINAL_REPORT.pdf from real report text and browser screenshots.');
} finally { await browser.close(); }