import { ArrowUpRight, Check, Clock3, FileWarning, LockKeyhole, ShieldCheck, ShieldX } from 'lucide-react';
import type { ScenarioResult, ScenarioStep } from '../types';
import { StatusBadge } from './StatusBadge';

function ActionStep({ step, onEvent }: { step: ScenarioStep; onEvent: (id: string) => void }) {
  return <><div className="timeline-step-top"><span className="eyebrow">{step.input_trust === 'untrusted' ? 'AGENT MANIPULATED · DANGEROUS PROPOSAL' : 'PROPOSED TOOL CALL'}</span>{step.decision && <StatusBadge decision={step.decision}/>}</div>
    <h3 className="tool-name">{step.tool}<span>.</span>{step.action}</h3>
    <div className="action-metadata"><span>{step.record_count?.toLocaleString()} {step.record_count === 1 ? 'record' : 'records'}</span><span>{step.destination || 'No destination specified'}</span><span>{step.contains_sensitive_data ? 'Sensitive data' : 'Non-sensitive data'}</span></div>
    <p className="step-description">{step.description}</p>
    <div className="interception"><ShieldCheck size={17}/><span>AgentGate intercepted</span><strong>{step.risk_score}<small> / 100</small></strong><span className={`severity ${step.severity?.toLowerCase()}`}>{step.severity}</span></div>
    {step.triggered_policies.length > 0 && <div className="policy-matches"><span className="eyebrow">POLICIES TRIGGERED</span>{step.triggered_policies.map(policy => <div className="policy-match" key={policy.policy_id}><ShieldX size={13}/><span>{policy.policy_id}</span></div>)}</div>}
    <div className="execution-line"><span>{step.executed ? <Check size={14}/> : <LockKeyhole size={14}/>}Tool executed: <strong>{step.executed ? 'YES · simulated' : 'NO'}</strong></span>{step.event_id && <button className="text-button" onClick={() => onEvent(step.event_id!)}>View audit event<ArrowUpRight size={13}/></button>}</div>
    {step.output && <details className="tool-output"><summary>Simulated tool output</summary><pre>{JSON.stringify(step.output.data, null, 2)}</pre><p>{step.output.message}</p></details>}
  </>;
}

export function ScenarioTimeline({ result, onEvent }: { result: ScenarioResult; onEvent: (id: string) => void }) {
  const titles = { SUCCESS: 'WORKFLOW COMPLETED', ATTACK_BLOCKED: 'ATTACK BLOCKED', APPROVAL_REQUIRED: 'HUMAN APPROVAL REQUIRED', STOPPED: 'WORKFLOW STOPPED' };
  const actions = result.steps.filter(step => step.tool);
  const noExecution = actions.length > 0 && actions.every(step => !step.executed);
  const Icon = result.status === 'SUCCESS' ? Check : result.status === 'APPROVAL_REQUIRED' ? Clock3 : ShieldCheck;
  return <div className="scenario-result"><div className="timeline-heading"><span className="eyebrow">EXECUTION TRACE</span><span>{result.steps.length} steps · {result.scenario_name}</span></div>
    <ol className="timeline">{result.steps.map(step => <li key={step.step_number} className={`timeline-item ${step.input_trust} ${step.tool ? 'tool-step' : ''}`}><span className="step-number">{String(step.step_number).padStart(2, '0')}</span><div className="step-content">{step.tool ? <ActionStep step={step} onEvent={onEvent}/> : <><span className={`trust-label ${step.input_trust}`}>{step.input_trust === 'untrusted' && <FileWarning size={13}/>} {step.input_trust === 'trusted' ? 'TRUSTED · USER REQUEST' : 'UNTRUSTED INPUT · SUPPORT DOCUMENT'}</span><p>{step.description}</p><blockquote>{step.input_content}</blockquote></>}</div></li>)}</ol>
    <div className={`outcome ${result.status.toLowerCase()}`} role="status"><div className="outcome-icon"><Icon size={26}/></div><div><span className="eyebrow">RUNTIME OUTCOME</span><h3>{titles[result.status]}</h3><p>{result.summary}</p></div><div className="execution-verdict"><span>Protected tool executed</span><strong>{noExecution ? 'NO' : actions.some(step => step.executed) ? 'YES' : '—'}</strong><small>{noExecution ? 'Execution prevented' : 'Simulated tools only'}</small></div></div>
  </div>;
}
