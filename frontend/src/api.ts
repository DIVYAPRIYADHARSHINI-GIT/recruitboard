import type { Auth } from './types';

const configured = import.meta.env.VITE_API_BASE || '/api';
export const API = configured === '/api' ? configured : '/api'; // Never silently send credentials to a foreign origin.
let csrf = '';
export function setCsrf(value: string) { csrf = value; }

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && typeof options.body === 'string') headers.set('Content-Type', 'application/json');
  if (options.method && options.method !== 'GET') headers.set('X-CSRF-Token', csrf);
  let response: Response;
  try { response = await fetch(API + path, { ...options, headers, credentials: 'same-origin' }); }
  catch { throw new ApiError('We couldn’t reach RecruitBoard. Check your connection and try again. A sleeping demo server can take about a minute to wake.', 0); }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(typeof body?.detail === 'string' ? body.detail : 'Something went wrong. Please try again in a moment.', response.status);
  }
  return response.json() as Promise<T>;
}

export async function authenticate(path: string, data?: object): Promise<Auth> {
  const result = await api<Auth>(path, data ? { method: 'POST', body: JSON.stringify(data) } : {});
  setCsrf(result.csrf);
  return result;
}

export function mutate<T>(path: string, method: string, data?: object) {
  return api<T>(path, { method, body: data ? JSON.stringify(data) : undefined });
}

export function uploadResume(candidate: number, file: File) {
  return api(`/candidates/${candidate}/resume`, { method: 'PUT', body: file, headers: { 'Content-Type': file.type, 'X-Filename': encodeURIComponent(file.name) } });
}