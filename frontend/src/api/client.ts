import type { Scenario, ScenarioResult, SecurityEvent } from '../types';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

async function request<T>(path: string, method = 'GET'): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { method, signal: controller.signal });
    if (!response.ok) throw new Error(`AgentGate API returned HTTP ${response.status}. Please check the backend and try again.`);
    return await response.json() as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('The API did not respond within 15 seconds. Check the event log before repeating a scenario; it may have completed.');
    }
    if (error instanceof TypeError) throw new Error('Cannot reach AgentGate. Start the backend at the configured API address, then retry.');
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  health: () => request<{ status: string; service: string }>('/api/health'),
  events: () => request<SecurityEvent[]>('/api/events'),
  scenarios: () => request<Scenario[]>('/api/scenarios'),
  runScenario: (id: string) => request<ScenarioResult>(`/api/scenarios/${encodeURIComponent(id)}/run`, 'POST'),
};
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : 'An unexpected error occurred. Please retry.';
