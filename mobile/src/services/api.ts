import { API_BASE_URL } from '../config/env';

const REQUEST_TIMEOUT_MS = 10_000;
const MAX_RETRIES = 2;
const RETRY_BASE_MS = 800;

function isNetworkError(err: unknown): boolean {
  if (!(err instanceof Error)) return false;
  return (
    err.name === 'AbortError' ||
    err.message.includes('Network request failed') ||
    err.message.includes('Failed to fetch') ||
    err.message.includes('timeout')
  );
}

async function request<T>(
  method: string,
  path: string,
  body?: Record<string, unknown>,
  attempt = 0,
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Request failed: ${res.status}`);
    }

    return res.json();
  } catch (err) {
    clearTimeout(timer);

    if (isNetworkError(err) && attempt < MAX_RETRIES) {
      const delay = RETRY_BASE_MS * Math.pow(2, attempt);
      await new Promise(r => setTimeout(r, delay));
      return request<T>(method, path, body, attempt + 1);
    }

    throw err;
  }
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: Record<string, unknown>) =>
    request<T>('POST', path, body),
  put: <T>(path: string, body: Record<string, unknown>) =>
    request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};
