import type { LucideIcon } from 'lucide-react';

export function MetricCard({ label, value, note, icon: Icon, tone = '' }: { label: string; value: number | null; note: string; icon: LucideIcon; tone?: string }) {
  return <div className={`metric-card ${tone}`}><div className="metric-label">{label}<Icon size={17} aria-hidden="true"/></div><strong>{value === null ? '—' : value.toLocaleString()}</strong><span className="metric-note">{note}</span></div>;
}
