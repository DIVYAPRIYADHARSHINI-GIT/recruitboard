export const STAGE_KEYS = ['applied', 'screening', 'interview', 'offer', 'hired', 'rejected'] as const;
export const SOURCE_LABELS: Record<string, string> = { referral: 'Referral', job_portal: 'Job portal', campus: 'Campus', website: 'Website' };
export function title(value: string) { return value.replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase()); }
export function initials(name: string) { return name.split(/\s+/).slice(0, 2).map(x => x[0] || '').join('').toUpperCase(); }
export function dateLabel(value: string, short = false) { return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', ...(short ? {} : { year: 'numeric' }) }).format(new Date(value)); }
export function timeLabel(value: string) { return new Intl.DateTimeFormat('en-IN', { hour: 'numeric', minute: '2-digit' }).format(new Date(value)); }
export function percentage(value: number | null) { return value === null ? '—' : `${value}%`; }
export function resumeError(file: { name: string; type: string; size: number }) {
  if (!file.name.toLowerCase().endsWith('.pdf') || file.type !== 'application/pdf') return 'Choose a PDF file (.pdf).';
  if (file.size > 1048576) return 'PDF must be at most 1 MB (1,048,576 bytes).';
  if (file.size === 0) return 'This file is empty. Choose another PDF.';
  return '';
}
export function queryString(values: Record<string, string | number>) { return new URLSearchParams(Object.entries(values).filter(([, value]) => value !== '').map(([key, value]) => [key, String(value)])).toString(); }