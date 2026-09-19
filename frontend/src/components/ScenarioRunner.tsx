import { ArrowRight, FlaskConical, LoaderCircle, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import { useRef, useState } from 'react';
import { api, errorMessage } from '../api/client';
import type { Scenario, ScenarioResult } from '../types';
import { ScenarioTimeline } from './ScenarioTimeline';

export function ScenarioRunner({ scenarios, loading, loadError, onRetry, onComplete, onEvent }: {
  scenarios: Scenario[]; loading: boolean; loadError: string; onRetry: () => void;
  onComplete: () => Promise<void>; onEvent: (id: string) => void;
}) {
  const [selected, setSelected] = useState('prompt-injection');
  const [running, setRunning] = useState(false);
  const runLock = useRef(false);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [error, setError] = useState('');
  const scenario = scenarios.find(item => item.id === selected) ?? scenarios[0];
  const isAttack = scenario?.id === 'prompt-injection';
  async function run() {
    if (!scenario || runLock.current) return;
    runLock.current = true;
    setRunning(true); setError(''); setResult(null);
    try { setResult(await api.runScenario(scenario.id)); }
    catch (cause) { setError(errorMessage(cause)); }
    finally { await onComplete(); setRunning(false); runLock.current = false; }
  }
  return <section className="panel simulation-panel" id="simulation" aria-labelledby="simulation-title" aria-busy={running}>
    <div className="panel-heading"><div><span className="eyebrow">SEE THE BOUNDARY IN ACTION</span><h2 id="simulation-title">An agent can be manipulated.<br/><span>The rules can’t.</span></h2></div><span className="subtle-tag"><FlaskConical size={13}/>SIMULATION LAB</span></div>
    <p className="panel-intro">Follow an agent from instruction to action. See exactly where AgentGate steps in.</p>
    {loadError && <div role="alert" className="error-box"><p>{loadError}</p><button className="text-button" onClick={onRetry} disabled={loading}>Retry connection <RotateCcw size={13}/></button></div>}
    {loading && scenarios.length === 0 ? <div className="loading-state" role="status"><LoaderCircle className="spin" size={18}/>Loading scenarios…</div> : <>
      <div className="scenario-tabs" role="group" aria-label="Choose a simulation">{scenarios.map((item, index) => <button key={item.id} disabled={running} aria-pressed={scenario?.id === item.id} onClick={() => { setSelected(item.id); setResult(null); setError(''); }}><span>0{index + 1}</span>{item.id === 'normal-support' ? 'Normal workflow' : item.id === 'prompt-injection' ? 'Prompt injection' : item.id === 'destructive-approval' ? 'Human approval' : item.name}</button>)}</div>
      {scenario && <div className="scenario-brief"><div><span className="eyebrow">{isAttack ? 'INDIRECT PROMPT INJECTION' : scenario.id === 'normal-support' ? 'LEGITIMATE TOOL USE' : 'DESTRUCTIVE ACTION'}</span><p>{scenario.description}</p></div><button className="primary-button" disabled={running || loading} onClick={() => void run()}>{running ? <LoaderCircle size={16} className="spin"/> : <Play size={15} fill="currentColor"/>}{running ? 'Running simulation…' : isAttack ? 'Run Attack Simulation' : 'Run Simulation'}</button></div>}
    </>}
    {error && <div className="error-box" role="alert">{error}</div>}
    {result ? <ScenarioTimeline result={result} onEvent={onEvent}/> : <div className="simulation-idle"><div className="idle-boundary"><span>AI AGENT</span><ArrowRight size={18}/><ShieldCheck size={33}/><ArrowRight size={18}/><span>TOOLS</span></div><h3>{running ? 'Evaluating proposed actions…' : 'The agent proposes. AgentGate decides.'}</h3><p>{running ? 'Policy checks and audit records are handled by the backend.' : 'Run a scenario to inspect the trust boundary, policy decisions, and actual tool execution.'}</p><span className="idle-label">DETERMINISTIC AGENT · SIMULATED TOOLS · LIVE POLICY ENGINE</span></div>}
    <div className="panel-footnote"><span className="local-dot"/>No real LLM. No real customer data. No emails sent.</div>
  </section>;
}
