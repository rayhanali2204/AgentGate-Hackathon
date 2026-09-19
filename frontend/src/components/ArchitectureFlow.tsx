import { ArrowDown, Bot, Database, Fingerprint, ShieldCheck } from 'lucide-react';

export function ArchitectureFlow() {
  return <section className="panel architecture" id="architecture" aria-labelledby="architecture-title"><div className="panel-heading"><div><span className="eyebrow">THE SECURITY BOUNDARY</span><h2 id="architecture-title">Trust nothing. Verify every action.</h2></div></div>
    <div className="flow-node"><Bot size={20}/><span>AI Agent<small>Proposes a tool call</small></span></div><ArrowDown className="flow-arrow" size={16}/>
    <div className="gateway-node"><div><ShieldCheck size={22}/><strong>AgentGate</strong><span>INTERCEPT</span></div><div className="engines"><span>Policy engine</span><span>Risk engine</span></div></div><ArrowDown className="flow-arrow" size={16}/>
    <div className="flow-node"><Database size={20}/><span>Protected Tools<small>Execute only after ALLOW</small></span><Fingerprint className="flow-fingerprint" size={20}/></div>
    <div className="principle"><span className="mini-rule"/><p>We don’t need to trust the agent.<br/><strong>We control what it can do.</strong></p></div>
  </section>;
}
