import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const ROOT = path.resolve('..');
const base = process.env.TEST_BASE_URL || 'http://127.0.0.1:4173';
const live = !['localhost', '127.0.0.1'].includes(new URL(base).hostname);
const run = new Date().toISOString().replace(/[:.]/g, '-');
const prefix = live ? 'live' : 'local';
await fs.mkdir(path.join(ROOT, '.browser/tmp'), { recursive: true });
await fs.mkdir(path.join(ROOT, 'screenshots'), { recursive: true });
await fs.mkdir(path.join(ROOT, 'bugs'), { recursive: true });
await fs.mkdir(path.join(ROOT, 'evidence'), { recursive: true });
if (live) {
  assert.equal(process.env.ALLOW_LIVE_ONCE, 'yes', 'Live suite requires explicit service permission and ALLOW_LIVE_ONCE=yes.');
  await fs.writeFile(path.join(ROOT, 'evidence/live-suite-started.json'), JSON.stringify({ started: run, origin: new URL(base).origin }), { flag: 'wx' });
}
const browser = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, downloadsPath: path.join(ROOT, '.browser/downloads'), args: ['--disable-background-networking', '--disable-component-update'] });
const results = [], errors = [], created = [];
let expectedNetwork = false;
async function context(width = 1440, height = 1000) {
  const context = await browser.newContext({ viewport: { width, height }, locale: 'en-IN', timezoneId: 'Asia/Kolkata', reducedMotion: 'reduce' });
  const page = await context.newPage();
  page.setDefaultTimeout(live ? 75000 : 12000);
  page.on('pageerror', e => errors.push({ kind: 'pageerror', message: e.message }));
  page.on('console', msg => { if (msg.type() === 'error' && !expectedNetwork) errors.push({ kind: 'console', message: msg.text() }); });
  return { context, page };
}
async function shot(page, name) { await page.screenshot({ path: path.join(ROOT, 'screenshots', `${prefix}-${name}.png`), fullPage: true, animations: 'disabled' }); }
async function check(name, page, fn) {
  try { await fn(); results.push({ name, passed: true }); console.log(`PASS ${name}`); }
  catch (error) {
    const stem = `${run}-${prefix}-${name.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`;
    await page.screenshot({ path: path.join(ROOT, 'bugs', `${stem}.png`), fullPage: true }).catch(() => {});
    await fs.writeFile(path.join(ROOT, 'bugs', `${stem}.txt`), `Browser check: ${name}\nOrigin: ${new URL(base).origin}\nTime: ${run}\n${error.stack}\n`);
    results.push({ name, passed: false, diagnostic: stem });
    console.error(`FAIL ${name}: ${error.message}`);
    throw error;
  }
}
async function go(page, url, heading) {
  await page.goto(base+url);
  if (heading) await page.getByRole('heading', { name: heading, exact: true }).waitFor();
  else await page.locator('.page-heading, .profile-heading, .hero, .signin-form').first().waitFor();
}
async function login(page, role) {
  await go(page, '/signin', 'Good to see you.');
  await page.getByRole('button', { name: `Try demo ${role}` }).click();
  await page.waitForURL(role === 'interviewer' ? '**/interviews' : '**/jobs');
  await page.locator('.page-heading').waitFor();
}
async function request(page, url, method = 'GET', body) {
  return page.evaluate(async ({ url, method, body }) => {
    const session = await fetch('/api/auth/session').then(r => r.json());
    const response = await fetch('/api'+url, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf }, ...(body === undefined ? {} : { body: JSON.stringify(body) }) });
    return { status: response.status, data: await response.json().catch(() => null) };
  }, { url, method, body });
}
async function audit(page, name) {
  const result = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  const violations = result.violations.map(v => ({ id: v.id, impact: v.impact, description: v.description, targets: v.nodes.map(n => n.target) }));
  if (violations.length) await fs.writeFile(path.join(ROOT, 'bugs', `${run}-${prefix}-axe-${name}.json`), JSON.stringify(violations, null, 2));
  assert.deepEqual(violations, [], `${name}: ${violations.map(v => v.id).join(', ')}`);
}
async function noOverflow(page) { assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+1), 'Document has horizontal overflow'); }
async function screenshotAudit(page, name) {
  await shot(page, name);
  await check(`accessibility-${name}`, page, () => audit(page, name));
  await check(`layout-${name}`, page, () => noOverflow(page));
}
async function addCandidate(page, name, email) {
  await page.getByRole('button', { name: 'Add candidate', exact: true }).click();
  await page.getByLabel('Full name', { exact: true }).fill(name);
  await page.getByLabel('Email address', { exact: true }).fill(email);
  const job = page.getByLabel('Job', { exact: true });
  await job.selectOption(String(primaryJobId));
  await page.getByLabel('Source', { exact: true }).selectOption('referral');
  await page.getByLabel('Tags (comma separated)').fill('TEST, portfolio');
  await page.getByLabel('Notes', { exact: true }).fill('TEST fictional candidate. Please remove at the end of this run.');
  await page.getByRole('button', { name: 'Add candidate', exact: true }).last().click();
  await page.getByRole('heading', { name, exact: true }).waitFor();
  const id = Number(new URL(page.url()).pathname.split('/').at(-1));
  created.push({ id, label: name, cleaned: false });
  return id;
}

const recruiter = await context();
const interviewer = await context();
const admin = await context();
let mainId, otherId, applicationId, scheduledId, primaryJobId, primaryJobTitle, demoInterviewerId, rejectionReasonId;
const candidateName = `TEST Journey ${run.slice(11,19)}`;
const candidateEmail = `test.journey.${Date.now()}@example.invalid`;
let failure;
try {
  await check('home-renders-original-product', recruiter.page, async () => { await go(recruiter.page, '/', /Make room for/); await shot(recruiter.page, 'home'); });
  await screenshotAudit(recruiter.page, 'home');
  await check('signin-and-demo-choices', recruiter.page, async () => { await go(recruiter.page, '/signin', 'Good to see you.'); assert.equal(await recruiter.page.locator('.demo-option').count(), 3); });
  await screenshotAudit(recruiter.page, 'signin');
  await check('recruiter-demo-signin-same-origin-cookie', recruiter.page, async () => {
    await login(recruiter.page, 'recruiter');
    const jobs = (await request(recruiter.page, '/jobs')).data;
    const primary = jobs.find(j => j.title === 'Senior Product Designer' && j.status === 'open') || jobs.find(j => j.status === 'open');
    assert.ok(primary, 'The demo needs an open job before its journey can run.');
    primaryJobId = primary.id; primaryJobTitle = primary.title;
    demoInterviewerId = (await request(recruiter.page, '/interviewers')).data.find(u => u.name === 'Demo Interviewer')?.id;
    rejectionReasonId = (await request(recruiter.page, '/settings')).data.rejection_reasons.find(r => r.active)?.id;
    assert.ok(demoInterviewerId && rejectionReasonId, 'Required fictional demo metadata is missing.');
    const cookie = (await recruiter.context.cookies()).find(c => c.name === 'rb_session');
    assert.ok(cookie?.httpOnly); assert.equal(cookie.sameSite, 'Lax');
    assert.equal(cookie.domain, new URL(base).hostname);
    if (live) assert.equal(cookie.secure, true);
    assert.equal(await recruiter.page.evaluate(() => document.cookie.includes('rb_session')), false);
    await recruiter.page.reload(); await recruiter.page.getByRole('heading', { name: 'Let’s build your next great team.' }).waitFor();
  });
  await screenshotAudit(recruiter.page, 'jobs');
  await check('kanban-six-stages-and-counts', recruiter.page, async () => { await go(recruiter.page, `/jobs/${primaryJobId}`, primaryJobTitle); assert.equal(await recruiter.page.locator('.kanban-column').count(), 6); assert.ok(await recruiter.page.locator('.candidate-card').count() > 0); });
  await screenshotAudit(recruiter.page, 'kanban');
  await check('recruiter-add-candidate', recruiter.page, async () => { mainId = await addCandidate(recruiter.page, candidateName, candidateEmail); const response = await request(recruiter.page, `/candidates/${mainId}`); applicationId = response.data.applications[0].id; });
  await screenshotAudit(recruiter.page, 'candidate-profile');
  await check('resume-upload-download-through-proxy', recruiter.page, async () => {
    const pdf = Buffer.from('%PDF-1.4\n1 0 obj<<>>endobj\n%%EOF');
    await recruiter.page.getByLabel('Upload resume PDF').setInputFiles({ name: 'TEST-resume.pdf', mimeType: 'application/pdf', buffer: pdf });
    await recruiter.page.getByText('Resume ready to review', { exact: true }).waitFor();
    const [download] = await Promise.all([recruiter.page.waitForEvent('download'), recruiter.page.getByRole('link', { name: 'Download resume' }).click()]);
    assert.equal(download.suggestedFilename(), 'resume.pdf');
  });
  await check('candidate-notes-edit', recruiter.page, async () => {
    await recruiter.page.getByRole('button', { name: 'Edit notes', exact: true }).click();
    await recruiter.page.getByLabel('Notes', { exact: true }).fill('TEST updated notes visible only to the recruiting team and assigned interviewers.');
    await recruiter.page.getByRole('button', { name: 'Save details' }).click();
    await recruiter.page.getByText('TEST updated notes visible only to the recruiting team and assigned interviewers.', { exact: true }).waitFor();
  });
  await check('keyboard-only-board-move', recruiter.page, async () => {
    await go(recruiter.page, `/jobs/${primaryJobId}`, primaryJobTitle);
    const select = recruiter.page.getByLabel(`Move ${candidateName} to stage`);
    await select.focus(); await recruiter.page.keyboard.press('s'); await recruiter.page.keyboard.press('Enter');
    await recruiter.page.getByRole('status').filter({ hasText: 'Moved to Screening.' }).waitFor();
    assert.equal((await request(recruiter.page, `/applications/${applicationId}`)).data.stage, 'screening');
  });
  await check('drag-and-drop-board-move', recruiter.page, async () => {
    const card = recruiter.page.locator('.candidate-card').filter({ has: recruiter.page.getByRole('link', { name: candidateName, exact: true }) });
    await card.dragTo(recruiter.page.locator('.kanban-column').filter({ has: recruiter.page.getByRole('heading', { name: 'Interview', exact: true }) }));
    await recruiter.page.getByRole('status').filter({ hasText: 'Application moved to Interview.' }).waitFor();
    assert.equal((await request(recruiter.page, `/applications/${applicationId}`)).data.stage, 'interview');
  });
  await check('schedule-interview-with-in-app-notification', recruiter.page, async () => {
    await go(recruiter.page, `/candidates/${mainId}`, candidateName);
    await recruiter.page.getByRole('button', { name: 'Schedule interview', exact: true }).click();
    await recruiter.page.getByLabel('Interviewer', { exact: true }).selectOption(String(demoInterviewerId));
    await recruiter.page.getByLabel('Interview date and time').fill('2026-12-02T11:00');
    await recruiter.page.getByRole('button', { name: 'Schedule interview', exact: true }).last().click();
    await recruiter.page.getByText('Waiting for the interviewer’s perspective.', { exact: true }).waitFor();
    const profile = (await request(recruiter.page, `/candidates/${mainId}`)).data; scheduledId = profile.interviews[0].id;
  });
  await check('create-unassigned-test-candidate', recruiter.page, async () => { await go(recruiter.page, '/candidates', 'Your talent, in one place.'); otherId = await addCandidate(recruiter.page, `TEST Unassigned ${run.slice(11,19)}`, `test.unassigned.${Date.now()}@example.invalid`); });
  await check('interviewer-demo-and-assigned-list', interviewer.page, async () => {
    await login(interviewer.page, 'interviewer');
    await interviewer.page.getByRole('link', { name: candidateName, exact: true }).waitFor();
    const data = (await request(interviewer.page, '/candidates')).data;
    assert.ok(data.items.some(c => c.id === mainId)); assert.ok(!data.items.some(c => c.id === otherId));
  });
  await screenshotAudit(interviewer.page, 'interviews');
  await check('interviewer-unassigned-profile-resume-denied', interviewer.page, async () => {
    expectedNetwork = true;
    assert.equal((await request(interviewer.page, `/candidates/${otherId}`)).status, 404);
    assert.equal((await request(interviewer.page, `/candidates/${otherId}/resume`)).status, 404);
    assert.equal((await request(interviewer.page, '/reports')).status, 403);
    expectedNetwork = false;
  });
  await check('interviewer-assigned-profile-and-notes', interviewer.page, async () => { await go(interviewer.page, `/candidates/${mainId}`, candidateName); await interviewer.page.getByText('TEST updated notes visible only to the recruiting team and assigned interviewers.', { exact: true }).waitFor(); assert.equal(await interviewer.page.getByRole('button', { name: 'Edit profile', exact: true }).count(), 0); });
  await check('scorecard-form-renders', interviewer.page, async () => { await go(interviewer.page, `/interviews/${scheduledId}/scorecard`, 'Turn a conversation into clarity.'); });
  await screenshotAudit(interviewer.page, 'scorecard-form');
  await check('interviewer-submits-scorecard', interviewer.page, async () => {
    await interviewer.page.locator('input[name=technical][value="4"]').check();
    await interviewer.page.locator('input[name=communication][value="5"]').check();
    await interviewer.page.locator('input[name=culture][value="4"]').check();
    await interviewer.page.getByLabel('Overall recommendation').selectOption('strong_yes');
    await interviewer.page.getByLabel('Written feedback').fill('TEST fictional evidence: clear technical explanations and thoughtful collaboration examples.');
    await interviewer.page.getByRole('button', { name: 'Submit scorecard', exact: true }).click();
    await interviewer.page.getByRole('heading', { name: 'A considered perspective.' }).waitFor();
  });
  await check('recruiter-review-feedback-and-record-offer', recruiter.page, async () => {
    await go(recruiter.page, `/candidates/${mainId}`, candidateName);
    await recruiter.page.getByRole('button', { name: 'Interviews & feedback', exact: true }).click();
    await recruiter.page.getByText('Strong Yes', { exact: true }).waitFor();
    await recruiter.page.getByLabel(`Move ${candidateName} to stage`).selectOption('offer');
    await recruiter.page.getByRole('status').filter({ hasText: 'Moved to Offer.' }).waitFor();
    await recruiter.page.getByRole('button', { name: 'Offers', exact: true }).click();
    await recruiter.page.getByLabel('Fictional annual amount (INR, optional)').fill('1200000');
    await recruiter.page.getByRole('button', { name: 'Create draft offer' }).click();
    await recruiter.page.getByRole('button', { name: 'Update offer' }).waitFor();
    for (const status of ['sent', 'accepted']) {
      await recruiter.page.getByLabel('Offer status').selectOption(status);
      await recruiter.page.getByRole('button', { name: 'Update offer' }).click();
      await recruiter.page.waitForFunction(status => document.querySelector('select[name=status]')?.value === status && !document.querySelector('button[type=submit]')?.disabled, status);
      await recruiter.page.waitForTimeout(150);
    }
    assert.equal((await request(recruiter.page, `/applications/${applicationId}/offer`)).data.status, 'accepted');
    await recruiter.page.getByLabel(`Move ${candidateName} to stage`).selectOption('hired');
    await recruiter.page.getByRole('status').filter({ hasText: 'Moved to Hired.' }).waitFor();
  });
  await check('stage-history-actor-timestamps-complete', recruiter.page, async () => {
    const history = (await request(recruiter.page, `/applications/${applicationId}/history`)).data;
    assert.deepEqual(history.map(h => h.to_stage), ['applied', 'screening', 'interview', 'offer', 'hired']);
    assert.ok(history.every(h => h.actor_id && h.occurred_at));
  });
  await check('rejection-confirmation-and-required-reason', recruiter.page, async () => {
    await go(recruiter.page, `/candidates/${otherId}`);
    const profile = (await request(recruiter.page, `/candidates/${otherId}`)).data;
    await recruiter.page.getByLabel(`Move ${profile.name} to stage`).selectOption('rejected');
    await recruiter.page.getByRole('heading', { name: 'Confirm rejection' }).waitFor();
    await recruiter.page.getByRole('button', { name: 'Confirm rejection', exact: true }).click();
    assert.equal((await request(recruiter.page, `/applications/${profile.applications[0].id}`)).data.stage, 'applied');
    await recruiter.page.getByLabel('Rejection reason', { exact: true }).selectOption(String(rejectionReasonId));
    await recruiter.page.getByRole('button', { name: 'Confirm rejection', exact: true }).click();
    await recruiter.page.getByRole('status').filter({ hasText: 'Moved to Rejected.' }).waitFor();
  });
  await check('notifications-panel-scorecard-and-stage', recruiter.page, async () => { await recruiter.page.getByRole('button', { name: 'Open notifications' }).click(); await recruiter.page.getByRole('heading', { name: 'Your notifications' }).waitFor(); await recruiter.page.getByText('A new scorecard is ready to review.', { exact: true }).first().waitFor(); });
  await screenshotAudit(recruiter.page, 'notifications');
  await recruiter.page.getByRole('button', { name: 'Close dialog' }).click();
  await check('candidate-list-filters-pagination', recruiter.page, async () => {
    await go(recruiter.page, '/candidates', 'Your talent, in one place.');
    await recruiter.page.getByLabel('Search candidates', { exact: true }).fill(candidateName);
    await recruiter.page.getByLabel('Search candidates', { exact: true }).press('Enter');
    await recruiter.page.getByRole('link', { name: new RegExp(candidateName) }).first().waitFor();
    await recruiter.page.getByLabel('Filter by source').selectOption('referral');
    await recruiter.page.getByLabel('Filter by stage').selectOption('hired');
    await recruiter.page.getByLabel('Filter by tag').fill('test');
    await recruiter.page.getByLabel('Filter by interviewer').selectOption(String(demoInterviewerId));
    await recruiter.page.getByRole('link', { name: new RegExp(candidateName) }).first().waitFor();
    assert.equal(await recruiter.page.locator('tbody tr').count(), 1);
    await recruiter.page.getByRole('button', { name: 'Reset', exact: true }).click();
    await recruiter.page.getByRole('button', { name: 'Next page', exact: true }).click();
    await recruiter.page.getByText('Page 2', { exact: true }).waitFor();
  });
  await screenshotAudit(recruiter.page, 'candidates');
  await check('reports-with-real-aggregates', recruiter.page, async () => { await go(recruiter.page, '/reports', 'The story behind your hiring.'); await recruiter.page.locator('.funnel-row').first().waitFor(); assert.equal(await recruiter.page.locator('.funnel-row').count(), 5); });
  await screenshotAudit(recruiter.page, 'reports-light');
  await check('reports-csv-download', recruiter.page, async () => { const [download] = await Promise.all([recruiter.page.waitForEvent('download'), recruiter.page.getByRole('link', { name: 'Export CSV', exact: true }).click()]); assert.equal(download.suggestedFilename(), 'recruitboard-report.csv'); });
  await check('dark-theme-persists', recruiter.page, async () => { await recruiter.page.getByRole('button', { name: 'Switch to dark theme' }).click(); await recruiter.page.reload(); await recruiter.page.locator('.funnel-row').first().waitFor(); assert.equal(await recruiter.page.locator('html').getAttribute('data-theme'), 'dark'); });
  await screenshotAudit(recruiter.page, 'reports-dark');
  await check('admin-demo-signin-and-team', admin.page, async () => { await login(admin.page, 'admin'); await go(admin.page, '/admin', 'Set your team up for good hiring.'); await admin.page.getByText('Protected demo', { exact: true }).first().waitFor(); });
  await screenshotAudit(admin.page, 'admin-members');
  await check('admin-settings-save-and-restore', admin.page, async () => {
    await admin.page.getByRole('button', { name: 'Scorecard criteria', exact: true }).click();
    const form = admin.page.locator('.criteria-settings form').filter({ hasText: 'Technical' });
    const original = await form.getByLabel('Rating guidance').inputValue();
    await form.getByLabel('Rating guidance').fill('TEST guidance: use specific job-relevant evidence.'); await form.getByRole('button', { name: 'Save criterion' }).click();
    await admin.page.getByRole('status').filter({ hasText: 'Workspace settings saved.' }).waitFor();
    await form.getByLabel('Rating guidance').fill(original); await form.getByRole('button', { name: 'Save criterion' }).click();
    await admin.page.getByRole('status').filter({ hasText: 'Workspace settings saved.' }).waitFor();
  });
  await screenshotAudit(admin.page, 'admin-scorecards');
  await admin.page.getByRole('button', { name: 'Pipeline stages', exact: true }).click(); await screenshotAudit(admin.page, 'admin-stages');
  await admin.page.getByRole('button', { name: 'Rejection reasons', exact: true }).click(); await screenshotAudit(admin.page, 'admin-reasons');
  await check('admin-anonymizes-with-explicit-confirmation', admin.page, async () => {
    await go(admin.page, `/candidates/${otherId}`);
    await admin.page.getByRole('button', { name: 'Privacy actions', exact: true }).click();
    await admin.page.getByLabel('Type CONFIRM to continue').fill('CONFIRM');
    await admin.page.getByRole('button', { name: 'Confirm permanent action' }).click();
    await admin.page.getByRole('heading', { name: 'Anonymized candidate', exact: true }).waitFor();
  });
  await check('mobile-responsive-navigation-and-board', recruiter.page, async () => {
    await recruiter.page.setViewportSize({ width: 390, height: 844 });
    await go(recruiter.page, '/jobs', 'Let’s build your next great team.');
    await recruiter.page.getByRole('button', { name: 'Open navigation' }).click();
    await recruiter.page.locator('.sidebar.visible').waitFor();
    await recruiter.page.getByRole('button', { name: 'Close navigation', exact: true }).last().click();
  });
  await screenshotAudit(recruiter.page, 'mobile-dark');
  await recruiter.page.getByRole('button', { name: 'Switch to light theme' }).click(); await screenshotAudit(recruiter.page, 'mobile-light');
  await go(recruiter.page, `/jobs/${primaryJobId}`, primaryJobTitle); await screenshotAudit(recruiter.page, 'mobile-kanban');
  await check('admin-permanent-delete-cleans-test-candidates', admin.page, async () => {
    for (const candidate of created) {
      await go(admin.page, `/candidates/${candidate.id}`);
      await admin.page.getByRole('button', { name: 'Privacy actions', exact: true }).click();
      await admin.page.getByLabel('Privacy action', { exact: true }).selectOption('delete');
      await admin.page.getByLabel('Type CONFIRM to continue').fill('CONFIRM');
      await admin.page.getByRole('button', { name: 'Confirm permanent action' }).click();
      await admin.page.getByRole('heading', { name: 'Your talent, in one place.' }).waitFor();
      candidate.cleaned = true;
    }
  });
  await check('no-unexpected-browser-errors', recruiter.page, async () => assert.deepEqual(errors, []));
} catch (error) { failure = error; }
finally {
  // Cleanup stays in the same approved origin and never touches baseline fictional seed data.
  if (created.some(c => !c.cleaned)) {
    try {
      if (!admin.page.url().includes(base)) await login(admin.page, 'admin');
      const session = await request(admin.page, '/auth/session');
      if (session.data?.user?.role !== 'admin') await login(admin.page, 'admin');
      for (const candidate of created.filter(c => !c.cleaned)) {
        const response = await request(admin.page, `/candidates/${candidate.id}/privacy`, 'POST', { action: 'delete', confirmation: 'CONFIRM' });
        candidate.cleaned = response.status === 200 || response.status === 404;
      }
    } catch { console.error('Cleanup incomplete: see the explicitly listed test records in evidence.'); }
  }
  const report = { run, origin: base, chrome: browser.version(), passed: results.filter(r => r.passed).length, failed: results.filter(r => !r.passed).length, results, unexpectedBrowserErrors: errors, testCandidates: created, live };
  await fs.writeFile(path.join(ROOT, 'evidence', `${run}-${prefix}-browser-results.json`), JSON.stringify(report, null, 2));
  console.log(`Browser totals: ${report.passed} passed, ${report.failed} failed. Created ${created.length}; cleaned ${created.filter(c => c.cleaned).length}.`);
  await browser.close();
}
if (failure) process.exitCode = 1;
