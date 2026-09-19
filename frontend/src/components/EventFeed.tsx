import { ChevronLeft, ChevronRight, ListFilter, LoaderCircle, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import type { Decision, SecurityEvent, Severity } from '../types';
import { filterEvents, timestamp } from '../lib/events';
import { StatusBadge } from './StatusBadge';
import { EventDetail } from './EventDetail';

export function EventFeed({ events, loading, error, selectedId, onSelect, onRefresh }: {
  events: SecurityEvent[]; loading: boolean; error: string; selectedId: string | null;
  onSelect: (id: string) => void; onRefresh: () => void;
}) {
  const [decision, setDecision] = useState<Decision | ''>('');
  const [severity, setSeverity] = useState<Severity | ''>('');
  const [agent, setAgent] = useState('');
  const [page, setPage] = useState(0);
  const filtered = filterEvents(events, decision, severity, agent);
  const pageCount = Math.max(1, Math.ceil(filtered.length / 6));
  const currentPage = Math.min(page, pageCount - 1);
  const visible = filtered.slice(currentPage * 6, currentPage * 6 + 6);
  const selected = events.find(event => event.event_id === selectedId) ?? null;
  const agents = [...new Set(events.map(event => event.agent_id))];
  return <section className="panel activity-panel" id="activity" aria-labelledby="activity-title"><div className="activity-header"><div><span className="eyebrow">THE AUDIT TRAIL</span><h2 id="activity-title">Security activity <span className="count-tag">{events.length}</span></h2></div><button className="secondary-button" onClick={onRefresh} disabled={loading}><RefreshCw size={14} className={loading ? 'spin' : ''}/>{loading ? 'Refreshing…' : 'Refresh events'}</button></div>
    {error && <div role="alert" className="error-box">{error}{events.length > 0 && <p>Showing the last successfully loaded events. Counts may be stale.</p>}</div>}
    <div className="activity-layout"><div className="activity-list"><div className="filters"><ListFilter size={16}/><label><span className="sr-only">Filter by decision</span><select value={decision} onChange={event => { setDecision(event.target.value as Decision | ''); setPage(0); }}><option value="">All decisions</option><option value="ALLOW">ALLOW</option><option value="BLOCK">BLOCK</option><option value="REQUIRE_APPROVAL">REQUIRE APPROVAL</option></select></label><label><span className="sr-only">Filter by severity</span><select value={severity} onChange={event => { setSeverity(event.target.value as Severity | ''); setPage(0); }}><option value="">All severities</option>{['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map(value => <option key={value}>{value}</option>)}</select></label><label><span className="sr-only">Filter by agent</span><select value={agent} onChange={event => { setAgent(event.target.value); setPage(0); }}><option value="">All agents</option>{agents.map(value => <option key={value}>{value}</option>)}</select></label></div>
      {loading && events.length === 0 ? <div className="table-empty" role="status"><LoaderCircle className="spin"/>Loading security events…</div> : filtered.length === 0 ? <div className="table-empty"><ListFilter size={26}/><h3>{events.length ? 'No matching events' : error ? 'Event log unavailable' : 'Your audit trail starts here.'}</h3><p>{events.length ? 'Try another filter to find the event you need.' : error ? 'Check the API connection and refresh events.' : 'Run a simulation to see real authorization decisions from AgentGate.'}</p>{events.length > 0 && <button className="text-button" onClick={() => { setDecision(''); setSeverity(''); setAgent(''); setPage(0); }}>Clear filters</button>}</div> : <div className="table-scroll"><table><caption className="sr-only">Security events, newest first. Select an action to inspect its details.</caption><thead><tr><th>TOOL / ACTION</th><th>DECISION</th><th>RISK</th><th>TIME</th></tr></thead><tbody>{visible.map(event => <tr key={event.event_id} className={selectedId === event.event_id ? 'selected' : ''}><td><button aria-label={`Inspect ${event.tool}.${event.action} event ${event.event_id}`} aria-pressed={selectedId === event.event_id} className="event-select" onClick={() => onSelect(event.event_id)}><strong>{event.tool}<span>.{event.action}</span></strong><span>{event.resource}</span><small>{event.agent_id}</small></button></td><td><StatusBadge decision={event.decision}/></td><td><strong className="table-risk">{event.risk_score}</strong><span className={`severity ${event.severity.toLowerCase()}`}>{event.severity}</span></td><td><time dateTime={event.timestamp}>{timestamp(event.timestamp)}</time></td></tr>)}</tbody></table></div>}
      <div className="table-footer"><span>{filtered.length ? `${currentPage * 6 + 1}–${Math.min((currentPage + 1) * 6, filtered.length)} of ${filtered.length} events` : '0 events'} · Newest first</span><div><button aria-label="Previous event page" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}><ChevronLeft size={16}/></button><button aria-label="Next event page" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}><ChevronRight size={16}/></button></div></div>
    </div><EventDetail event={selected}/></div>
  </section>;
}
