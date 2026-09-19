import type { Decision, SecurityEvent, Severity } from '../types';

export function eventMetrics(events: SecurityEvent[]) {
  return {
    agents: new Set(events.map(event => event.agent_id)).size,
    total: events.length,
    blocked: events.filter(event => event.decision === 'BLOCK').length,
    approval: events.filter(event => event.decision === 'REQUIRE_APPROVAL').length,
  };
}
export function filterEvents(events: SecurityEvent[], decision: Decision | '', severity: Severity | '', agent: string) {
  return events.filter(event => (!decision || event.decision === decision) && (!severity || event.severity === severity) && (!agent || event.agent_id === agent));
}
export const timestamp = (value: string) => new Date(value).toLocaleString(undefined, { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' });
