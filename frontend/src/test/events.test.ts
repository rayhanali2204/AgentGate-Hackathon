import { describe, expect, it } from 'vitest';
import { eventMetrics, filterEvents } from '../lib/events';
import { attackEvent } from './fixtures';
import type { SecurityEvent } from '../types';

const events: SecurityEvent[] = [attackEvent, { ...attackEvent, event_id: 'safe', decision: 'ALLOW', severity: 'LOW', risk_score: 0 }, { ...attackEvent, event_id: 'pending', agent_id: 'another-agent', decision: 'REQUIRE_APPROVAL', severity: 'LOW', risk_score: 25 }];
describe('audit-derived metrics and filters', () => {
  it('counts unique agents and decisions rather than fabricating inventory', () => {
    expect(eventMetrics(events)).toEqual({ agents: 2, total: 3, blocked: 1, approval: 1 });
  });
  it('starts with zero metrics for an empty event log', () => {
    expect(eventMetrics([])).toEqual({ agents: 0, total: 0, blocked: 0, approval: 0 });
  });
  it('combines decision, severity and agent filters', () => {
    expect(filterEvents(events, 'BLOCK', 'CRITICAL', 'customer-support-agent')).toEqual([attackEvent]);
    expect(filterEvents(events, 'ALLOW', 'CRITICAL', '')).toEqual([]);
  });
});
