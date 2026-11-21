import { describe, expect, it, vi, afterEach } from 'vitest';
import { initials, percentage, queryString, resumeError, title } from '../src/helpers';
import { api, authenticate, setCsrf } from '../src/api';

afterEach(() => vi.unstubAllGlobals());
describe('presentation and upload validation', () => {
  it('formats initials', () => expect(initials('Mira Reed')).toBe('MR'));
  it('formats stage labels', () => expect(title('strong_yes')).toBe('Strong Yes'));
  it('does not fabricate empty percentages', () => expect(percentage(null)).toBe('—'));
  it('formats zero percentages honestly', () => expect(percentage(0)).toBe('0%'));
  it('encodes filter state', () => expect(queryString({ q: 'a+b', page: 2, stage: '' })).toBe('q=a%2Bb&page=2'));
  it.each(['resume.exe', 'resume.pdf.exe'])('rejects extension %s', name => expect(resumeError({ name, type: 'application/pdf', size: 10 })).not.toBe(''));
  it('rejects wrong MIME', () => expect(resumeError({ name: 'resume.pdf', type: 'text/plain', size: 20 })).not.toBe(''));
  it('rejects oversized file', () => expect(resumeError({ name: 'resume.pdf', type: 'application/pdf', size: 1048577 })).toContain('1 MB'));
  it('accepts exact limit', () => expect(resumeError({ name: 'resume.PDF', type: 'application/pdf', size: 1048576 })).toBe(''));
  it('rejects empty file', () => expect(resumeError({ name: 'resume.pdf', type: 'application/pdf', size: 0 })).toContain('empty'));
});
describe('same-origin API client', () => {
  it('attaches CSRF and same-origin credentials', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));
    vi.stubGlobal('fetch', fetcher); setCsrf('test-only-non-secret');
    await api('/jobs', { method: 'POST', body: '{}' });
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe('/api/jobs'); expect(options.credentials).toBe('same-origin');
    expect(options.headers.get('X-CSRF-Token')).toBe('test-only-non-secret');
  });
  it('uses friendly network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network')));
    await expect(api('/jobs')).rejects.toThrow('couldn’t reach');
  });
  it('preserves server duplicate warning', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"A candidate already exists."}', { status: 409 })));
    await expect(api('/candidates')).rejects.toThrow('already exists');
  });
  it('handles non-JSON proxy cold-start errors', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Gateway</html>', { status: 502 })));
    await expect(api('/jobs')).rejects.toThrow('try again');
  });
  it('updates CSRF on authentication', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response('{"user":null,"csrf":"rotated-test-value","demo":true}')).mockResolvedValueOnce(new Response('{}'));
    vi.stubGlobal('fetch', fetcher); await authenticate('/auth/session'); await api('/jobs', { method: 'POST' });
    expect(fetcher.mock.calls[1][1].headers.get('X-CSRF-Token')).toBe('rotated-test-value');
  });
});