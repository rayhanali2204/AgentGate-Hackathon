import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import App from '../App';
import { api } from '../api/client';
import { ScenarioTimeline } from '../components/ScenarioTimeline';
import { attackEvent, attackResult } from './fixtures';
import type { ScenarioResult } from '../types';

vi.mock('../api/client', () => ({
  API_BASE_URL: 'http://127.0.0.1:8000', errorMessage: (error: Error) => error.message,
  api: { health: vi.fn(), events: vi.fn(), scenarios: vi.fn(), runScenario: vi.fn() },
}));
afterEach(cleanup);
beforeEach(() => {
  vi.mocked(api.health).mockResolvedValue({ status: 'ok', service: 'AgentGate' });
  vi.mocked(api.events).mockResolvedValue([]);
  vi.mocked(api.scenarios).mockResolvedValue([{ id: 'prompt-injection', name: 'Indirect prompt injection', description: 'An untrusted support note manipulates the agent.' }]);
});
it('runs the attack, displays non-execution, and refreshes the event log', async () => {
  let resolveRun!: (value: ScenarioResult) => void;
  vi.mocked(api.runScenario).mockReturnValue(new Promise(resolve => { resolveRun = resolve; }));
  render(<App/>);
  const runButton = await screen.findByRole('button', { name: 'Run Attack Simulation' });
  await screen.findByText('Your audit trail starts here.');
  fireEvent.click(runButton);
  expect((screen.getByRole('button', { name: 'Running simulation…' }) as HTMLButtonElement).disabled).toBe(true);
  expect((screen.getByRole('button', { name: /Prompt injection/ }) as HTMLButtonElement).disabled).toBe(true);
  vi.mocked(api.events).mockResolvedValue([attackEvent]);
  resolveRun(attackResult);
  expect(await screen.findByText('ATTACK BLOCKED')).toBeTruthy();
  await waitFor(() => expect(api.events).toHaveBeenCalledTimes(2));
  expect(screen.getByRole('button', { name: /Inspect customer_database.read/ })).toBeTruthy();
  expect(screen.getByText('Execution prevented')).toBeTruthy();
  expect(screen.queryByText('YES · simulated')).toBeNull();
  fireEvent.change(screen.getByLabelText('Filter by decision'), { target: { value: 'ALLOW' } });
  expect(screen.getByText('No matching events')).toBeTruthy();
  fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(screen.getByRole('button', { name: /Inspect customer_database.read/ })).toBeTruthy();
});
it('shows unavailable and retry states without invented events', async () => {
  vi.mocked(api.events).mockRejectedValue(new Error('Backend is offline'));
  vi.mocked(api.scenarios).mockRejectedValue(new Error('Scenarios unavailable'));
  render(<App/>);
  expect(await screen.findByText('Event log unavailable')).toBeTruthy();
  expect(screen.getByText('API unavailable')).toBeTruthy();
  expect(screen.getByRole('button', { name: /Retry connection/ })).toBeTruthy();
  expect(screen.queryByRole('button', { name: /Inspect/ })).toBeNull();
});
it('keeps authorization and actual execution distinct for approval', () => {
  const result: ScenarioResult = { ...attackResult, status: 'APPROVAL_REQUIRED', steps: [{ ...attackResult.steps[0], action: 'delete', decision: 'REQUIRE_APPROVAL', risk_score: 25, severity: 'LOW', execution_status: 'PENDING_APPROVAL', triggered_policies: [] }] };
  render(<ScenarioTimeline result={result} onEvent={() => undefined}/>);
  expect(screen.getByText('HUMAN APPROVAL REQUIRED')).toBeTruthy();
  expect(screen.getByText('Execution prevented')).toBeTruthy();
  expect(screen.queryByText('YES · simulated')).toBeNull();
});
it('shows an executed normal workflow as completed', () => {
  const result: ScenarioResult = { ...attackResult, status: 'SUCCESS', steps: [{ ...attackResult.steps[0], input_trust: 'trusted', decision: 'ALLOW', executed: true, execution_status: 'EXECUTED', risk_score: 0, severity: 'LOW', triggered_policies: [] }] };
  render(<ScenarioTimeline result={result} onEvent={() => undefined}/>);
  expect(screen.getByText('WORKFLOW COMPLETED')).toBeTruthy();
  expect(screen.getByText('YES · simulated')).toBeTruthy();
});
