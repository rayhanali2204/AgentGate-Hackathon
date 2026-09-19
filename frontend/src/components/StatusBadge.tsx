import { Check, ShieldX, Clock3 } from 'lucide-react';
import type { Decision } from '../types';

export function StatusBadge({ decision }: { decision: Decision }) {
  const Icon = decision === 'ALLOW' ? Check : decision === 'BLOCK' ? ShieldX : Clock3;
  return <span className={`badge ${decision.toLowerCase()}`}><Icon size={12} aria-hidden="true" />{decision === 'REQUIRE_APPROVAL' ? 'REQUIRE APPROVAL' : decision}</span>;
}
