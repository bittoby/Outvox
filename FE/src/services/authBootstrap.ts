/**
 * Installs a global API-key header on axios requests.
 *
 * The backend's APIKeyAuthMiddleware (BE/core/auth.py) expects every mutating
 * call to carry the shared secret as `X-API-Key`. We pull the value from
 * `VITE_API_KEY` at build time, falling back to a value persisted in
 * `localStorage` so it can be set from the browser console without rebuilding.
 *
 * If neither source provides a key, no header is set and the dashboard will
 * fail against a backend that has `API_KEY` set. That is intentional — we
 * want loud, visible failure rather than a silent leak of access.
 */

import axios from 'axios';

const STORAGE_KEY = 'outvox.api_key';

function readApiKey(): string {
  const fromEnv = (import.meta.env.VITE_API_KEY ?? '').toString().trim();
  if (fromEnv) return fromEnv;
  try {
    const fromStorage = (window.localStorage.getItem(STORAGE_KEY) ?? '').trim();
    if (fromStorage) return fromStorage;
  } catch {
    /* ignore: localStorage may be blocked */
  }
  return '';
}

export function installApiKeyHeader(): void {
  const key = readApiKey();
  if (!key) {
    if (import.meta.env.DEV) {
      console.warn(
        '[Outvox] No API key configured. Set VITE_API_KEY in your .env, ' +
          'or call setApiKey("...") from the console. The backend will reject ' +
          'requests if it has API_KEY set.'
      );
    }
    return;
  }
  axios.defaults.headers.common['X-API-Key'] = key;
}

// Exposed for ad-hoc use from the browser console / DevTools.
declare global {
  interface Window {
    setApiKey: (value: string) => void;
    clearApiKey: () => void;
  }
}

if (typeof window !== 'undefined') {
  window.setApiKey = (value: string) => {
    const trimmed = (value ?? '').toString().trim();
    if (!trimmed) {
      window.clearApiKey();
      return;
    }
    try {
      window.localStorage.setItem(STORAGE_KEY, trimmed);
    } catch {
      /* ignore */
    }
    axios.defaults.headers.common['X-API-Key'] = trimmed;
  };
  window.clearApiKey = () => {
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
    delete axios.defaults.headers.common['X-API-Key'];
  };
}
