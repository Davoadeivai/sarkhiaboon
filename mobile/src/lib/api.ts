import { useAuth } from './auth';
import type { AuthResponse } from './types';

export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

/** An API failure with a Persian message that is safe to show to the customer. */
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public fields?: Record<string, string>,
  ) {
    super(message);
  }
}

const NETWORK_MESSAGE = 'اتصال به سرور برقرار نشد. اینترنت را بررسی کن و دوباره امتحان کن.';

/** Turn any DRF error body into one readable message (+ per-field messages for forms). */
function toApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object') {
    const data = body as Record<string, unknown>;
    if (typeof data.detail === 'string') {
      return new ApiError(data.detail, status, typeof data.code === 'string' ? data.code : undefined);
    }
    const fields: Record<string, string> = {};
    for (const [key, value] of Object.entries(data)) {
      const first = Array.isArray(value) ? value[0] : value;
      if (typeof first === 'string') fields[key] = first;
    }
    const firstMessage = Object.values(fields)[0];
    if (firstMessage) return new ApiError(firstMessage, status, 'invalid', fields);
  }
  if (status >= 500) return new ApiError('سرور موقتاً پاسخ نمی‌دهد. چند لحظه بعد دوباره امتحان کن.', status);
  return new ApiError('درخواست انجام نشد.', status);
}

type Body = Record<string, unknown> | FormData | undefined;

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: Body;
  /** Skip the Authorization header (login endpoints). */
  anonymous?: boolean;
}

async function rawRequest(path: string, opts: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  let body: BodyInit | undefined;
  if (opts.body instanceof FormData) {
    body = opts.body;
  } else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(opts.body);
  }
  if (token && !opts.anonymous) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${API_URL}/api/v1${path}`, { method: opts.method ?? 'GET', headers, body });
  } catch {
    throw new ApiError(NETWORK_MESSAGE, 0, 'network');
  }
}

let refreshing: Promise<boolean> | null = null;

/** Swap the refresh token for a new access token; falls back to a fresh guest session. */
async function renewSession(): Promise<boolean> {
  const { refresh, setAccess } = useAuth.getState();
  if (refresh) {
    const res = await rawRequest('/auth/token/refresh/', { method: 'POST', body: { refresh }, anonymous: true }, null);
    if (res.ok) {
      const data = (await res.json()) as { access: string };
      await setAccess(data.access);
      return true;
    }
  }
  await startGuestSession();
  return true;
}

/** Every visitor gets a guest account so they can browse and try on before signing in. */
export async function startGuestSession(): Promise<void> {
  const res = await rawRequest('/auth/guest/', { method: 'POST', anonymous: true }, null);
  if (!res.ok) throw toApiError(res.status, await res.json().catch(() => null));
  await useAuth.getState().setSession((await res.json()) as AuthResponse);
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await rawRequest(path, opts, useAuth.getState().access);

  if (res.status === 401 && !opts.anonymous) {
    refreshing ??= renewSession().finally(() => {
      refreshing = null;
    });
    await refreshing;
    res = await rawRequest(path, opts, useAuth.getState().access);
  }

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => null);
  if (!res.ok) throw toApiError(res.status, data);
  return data as T;
}

/** Build a query string, dropping empty values. */
export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '' && v !== false)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}
