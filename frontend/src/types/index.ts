export type Decision = 'ALLOW' | 'BLOCK' | 'REQUIRE_APPROVAL';
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export interface PolicyMatch { policy_id: string; decision: Decision; explanation: string }
export interface SecurityEvent {
  event_id: string;
  timestamp: string;
  agent_id: string;
  tool: string;
  action: string;
  resource: string;
  record_count: number;
  destination: string | null;
  contains_sensitive_data: boolean;
  decision: Decision;
  risk_score: number;
  severity: Severity;
  triggered_policies: PolicyMatch[];
  explanation: string;
}
export interface Scenario { id: string; name: string; description: string }
export interface ToolOutput { message: string; data: Record<string, string | number> }
export interface ScenarioStep {
  step_number: number;
  description: string;
  input_trust: 'trusted' | 'untrusted';
  input_content: string | null;
  tool: string | null;
  action: string | null;
  resource: string | null;
  record_count: number | null;
  destination: string | null;
  contains_sensitive_data: boolean | null;
  decision: Decision | null;
  risk_score: number | null;
  severity: Severity | null;
  triggered_policies: PolicyMatch[];
  explanation: string | null;
  executed: boolean;
  event_id: string | null;
  execution_status: 'EXECUTED' | 'BLOCKED' | 'PENDING_APPROVAL' | null;
  output: ToolOutput | null;
}
export interface ScenarioResult {
  scenario_id: string;
  scenario_name: string;
  status: 'SUCCESS' | 'ATTACK_BLOCKED' | 'APPROVAL_REQUIRED' | 'STOPPED';
  summary: string;
  steps: ScenarioStep[];
}
