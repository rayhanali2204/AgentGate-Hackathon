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
