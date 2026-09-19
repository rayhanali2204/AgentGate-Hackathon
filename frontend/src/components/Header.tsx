import { ArrowUpRight, BookOpen, LayoutDashboard, ListFilter, ShieldCheck, Terminal, Workflow, Zap } from 'lucide-react';
import { API_BASE_URL } from '../api/client';

export function Sidebar() {
  return <aside className="sidebar">
    <a className="brand" href="#overview"><span className="brand-mark"><ShieldCheck size={23}/></span>AgentGate<span className="brand-dot">.</span></a>
    <div className="workspace"><span className="workspace-icon">AG</span><span>Hackathon workspace<small>Local environment</small></span><span className="local-dot"/></div>
    <p className="nav-label">WORKSPACE</p>
    <nav aria-label="Main navigation">
      <a className="nav-link active" href="#overview"><LayoutDashboard size={17}/>Overview<span className="nav-active-dot"/></a>
      <a className="nav-link" href="#simulation"><Zap size={17}/>Simulation lab</a>
      <a className="nav-link" href="#activity"><ListFilter size={17}/>Security events</a>
      <a className="nav-link" href="#architecture"><Workflow size={17}/>Architecture</a>
    </nav>
    <div className="sidebar-bottom"><div className="sandbox-note"><Terminal size={18}/><strong>A safe place to test.</strong><p>Simulated agents. Fake tools.<br/>Real policy enforcement.</p><span className="eyebrow">DETERMINISTIC SANDBOX</span></div>
      <a className="nav-link" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer"><BookOpen size={17}/>API documentation<ArrowUpRight size={14}/></a>
      <div className="sidebar-footer"><span className="avatar">AG</span><span>AgentGate demo<small>Milestone 04</small></span></div>
    </div>
  </aside>;
}

export function Header({ connected, loading }: { connected: boolean | null; loading: boolean }) {
  return <header className="topbar"><div><span className="muted">Workspace</span><span className="breadcrumb">/</span><span>Security overview</span></div><div className="topbar-right"><span className="environment">LOCAL SANDBOX</span><span className={`connection ${connected ? 'online' : ''}`}><span className="status-dot"/>{loading ? 'Syncing API' : connected === null ? 'Connecting' : connected ? 'API connected' : 'API unavailable'}</span></div></header>;
}
