import { API_BASE_URL } from '../config/env';

const PING_TIMEOUT_MS = 4000;
const PING_PATH = '/api/stellar/station'; // lightweight GET, always available

let _lastResult: boolean = true;
let _lastChecked: number = 0;
const DEBOUNCE_MS = 10_000; // don't ping more than once per 10s

export async function checkConnectivity(): Promise<boolean> {
  const now = Date.now();
  if (now - _lastChecked < DEBOUNCE_MS) return _lastResult;

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PING_TIMEOUT_MS);
    const res = await fetch(`${API_BASE_URL}${PING_PATH}`, {
      method: 'HEAD',
      signal: controller.signal,
    });
    clearTimeout(timer);
    _lastResult = res.status < 500;
  } catch {
    _lastResult = false;
  }

  _lastChecked = Date.now();
  return _lastResult;
}

export function getLastConnectivityResult(): boolean {
  return _lastResult;
}
