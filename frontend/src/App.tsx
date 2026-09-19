import { Activity, ArrowDown, Clock3, Radio, ShieldBan, Users } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { api, errorMessage } from './api/client';
import { ArchitectureFlow } from './components/ArchitectureFlow';
import { EventFeed } from './components/EventFeed';
import { Header, Sidebar } from './components/Header';
import { MetricCard } from './components/MetricCard';
import { ScenarioRunner } from './components/ScenarioRunner';
import { eventMetrics } from './lib/events';
import type { Scenario, SecurityEvent } from './types';

export default function App() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [loadingScenarios, setLoadingScenarios] = useState(true);
  const [eventsError, setEventsError] = useState('');
  const [scenariosError, setScenariosError] = useState('');
  const [connected, setConnected] = useState<boolean | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [lastSync, setLastSync] = useState<Date | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const requestVersion = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++requestVersion.current;
    setLoadingEvents(true);
    try {
      const [data, health] = await Promise.all([api.events(), api.health()]);
      if (version !== requestVersion.current) return;
      setEvents(data); setConnected(health.status === 'ok'); setLoaded(true);
      setEventsError(''); setLastSync(new Date());
      setSelectedId(previous => data.some(event => event.event_id === previous) ? previous : data[0]?.event_id ?? null);
    } catch (error) {
      if (version !== requestVersion.current) return;
      setEventsError(errorMessage(error)); setConnected(false);
    } finally { if (version === requestVersion.current) setLoadingEvents(false); }
  }, []);
  const loadScenarios = useCallback(async () => {
    setLoadingScenarios(true); setScenariosError('');
    try { setScenarios(await api.scenarios()); }
    catch (error) { setScenariosError(errorMessage(error)); }
    finally { setLoadingScenarios(false); }
  }, []);
  useEffect(() => { void refresh(); void loadScenarios(); }, [refresh, loadScenarios]);
  const metrics = eventMetrics(events);
  function inspect(id: string) { setSelectedId(id); document.getElementById('activity')?.scrollIntoView({ behavior: 'instant' }); }
  return <><a className="skip-link" href="#overview">Skip to dashboard</a><Sidebar/><div className="app-shell"><Header connected={connected} loading={loadingEvents}/><main id="overview">
    <div className="page-heading"><div><div className="eyebrow heading-eyebrow"><span className="mint-square"/>ZERO-TRUST SECURITY FOR AUTONOMOUS AI AGENTS</div><h1>Autonomy, with boundaries.</h1><p>Every AI tool call is intercepted, evaluated and audited before execution.</p></div><a className="secondary-button demo-shortcut" href="#simulation">Explore the demo<ArrowDown size={15}/></a></div>
    <div className="section-caption"><span><Radio size={13}/>RUNTIME OVERVIEW</span><span>{eventsError ? 'Last known data · API unavailable' : lastSync ? `Last synced ${lastSync.toLocaleTimeString()}` : 'Waiting for API data'} · In-memory session</span></div>
    <div className="metrics"><MetricCard label="Observed agents" value={loaded ? metrics.agents : null} note="Unique agents in the audit log" icon={Users}/><MetricCard label="Total actions" value={loaded ? metrics.total : null} note="Evaluated by the policy engine" icon={Activity}/><MetricCard label="Blocked actions" value={loaded ? metrics.blocked : null} note="Denied by security policies" icon={ShieldBan} tone="blocked-metric"/><MetricCard label="Approval required" value={loaded ? metrics.approval : null} note="Not authorized to run automatically" icon={Clock3} tone="approval-metric"/></div>
    <div className="demo-grid"><ScenarioRunner scenarios={scenarios} loading={loadingScenarios} loadError={scenariosError} onRetry={() => { void loadScenarios(); void refresh(); }} onComplete={refresh} onEvent={inspect}/><div className="context-column"><ArchitectureFlow/><div className="concept-note"><span className="eyebrow">SECURITY, BEYOND THE PROMPT</span><p>Detecting every malicious instruction is hard.<br/><strong>Controlling tool access shouldn’t be.</strong></p><div><span>ALLOW</span><span>BLOCK</span><span>REQUIRE APPROVAL</span></div></div></div></div>
    <EventFeed events={events} loading={loadingEvents} error={eventsError} selectedId={selectedId} onSelect={setSelectedId} onRefresh={() => void refresh()}/>
    <footer className="page-footer"><span>AgentGate <span className="muted">/</span> Runtime security for the agentic era.</span><span>DETERMINISTIC DEMO <span className="mint-square"/> MILESTONE 04</span></footer>
  </main></div></>;
}
