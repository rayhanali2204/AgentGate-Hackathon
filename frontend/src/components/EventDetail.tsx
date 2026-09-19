import { Fingerprint, ShieldCheck } from 'lucide-react';
import type { SecurityEvent } from '../types';
import { timestamp } from '../lib/events';
import { StatusBadge } from './StatusBadge';

export function EventDetail({ event }: { event: SecurityEvent | null }) {
  return <aside className="event-detail" aria-label="Selected event details" aria-live="polite"><div className="detail-heading"><span className="eyebrow">EVENT INSPECTOR</span><Fingerprint size={18}/></div>{event ? <>
    <div className="detail-title"><h3>{event.tool}<span>.{event.action}</span></h3><StatusBadge decision={event.decision}/></div>
    <div className="detail-risk"><strong>{event.risk_score}<small>/100</small></strong><span className={`severity ${event.severity.toLowerCase()}`}>{event.severity} RISK</span><div className="risk-track"><span style={{ width: `${event.risk_score}%` }}/></div></div>
    <dl><dt>Agent</dt><dd>{event.agent_id}</dd><dt>Resource</dt><dd>{event.resource}</dd><dt>Destination</dt><dd>{event.destination ?? 'Not specified'}</dd><dt>Records</dt><dd>{event.record_count.toLocaleString()}</dd><dt>Sensitive data</dt><dd>{event.contains_sensitive_data ? 'Yes' : 'No'}</dd><dt>Recorded</dt><dd>{timestamp(event.timestamp)}</dd></dl>
    <div className="detail-policies"><h4>Triggered policies <span>{event.triggered_policies.length}</span></h4>{event.triggered_policies.length ? event.triggered_policies.map(policy => <div key={policy.policy_id}><code>{policy.policy_id}</code><p>{policy.explanation}</p></div>) : <p>No restrictive policy matched.</p>}</div>
    <details className="explanation" open><summary>Decision explanation</summary><p>{event.explanation}</p></details>
    <p className="audit-note">This audit records authorization, not proof of tool execution. Execution is shown in the simulation trace.</p><code className="event-id">{event.event_id}</code>
  </> : <div className="detail-empty"><ShieldCheck size={28}/><h3>Every decision has a reason.</h3><p>Select an event to inspect its policy matches, risk score, and explanation.</p></div>}</aside>;
}
