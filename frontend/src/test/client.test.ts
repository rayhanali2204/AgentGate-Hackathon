import { afterEach, expect, it, vi } from 'vitest';
import { api } from '../api/client';

afterEach(() => { vi.unstubAllGlobals(); });
it('uses the POST scenario endpoint and escapes its identifier', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'SUCCESS' }) });
  vi.stubGlobal('fetch', fetchMock);
  await api.runScenario('scenario/name');
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/scenarios/scenario%2Fname/run'), expect.objectContaining({ method: 'POST' }));
});
it('turns network errors into useful connection guidance', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  await expect(api.events()).rejects.toThrow('Cannot reach AgentGate');
});
it('handles HTTP errors without displaying arbitrary server content', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
  await expect(api.events()).rejects.toThrow('HTTP 500');
});

it('defaults production API requests to the same origin', async () => {
  vi.stubEnv('DEV', false);
  vi.stubEnv('VITE_API_BASE_URL', undefined);
  vi.resetModules();
  const { api: productionApi, API_BASE_URL } = await import('../api/client');
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'ok' }) });
  vi.stubGlobal('fetch', fetchMock);
  expect(API_BASE_URL).toBe('');
  await productionApi.health();
  expect(fetchMock).toHaveBeenCalledWith('/api/health', expect.any(Object));
});

it('retains the separate development backend default', async () => {
  vi.stubEnv('DEV', true);
  vi.stubEnv('VITE_API_BASE_URL', undefined);
  vi.resetModules();
  expect((await import('../api/client')).API_BASE_URL).toBe('http://127.0.0.1:8000');
});

it('honors an explicit API override and an explicit same-origin setting', async () => {
  vi.stubEnv('VITE_API_BASE_URL', 'https://gateway.example/');
  vi.resetModules();
  expect((await import('../api/client')).API_BASE_URL).toBe('https://gateway.example');
  vi.stubEnv('VITE_API_BASE_URL', '');
  vi.resetModules();
  expect((await import('../api/client')).API_BASE_URL).toBe('');
});

afterEach(() => { vi.unstubAllEnvs(); vi.resetModules(); });
