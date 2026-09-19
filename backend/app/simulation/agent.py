"""Scripted agent: deliberately follows an injected note in the attack demo.

This is not an LLM or an injection-text detector. Only the runtime gateway
controls whether each proposed action reaches a fake adapter.
"""

from ..models import Decision, ToolRequest
from ..permissions import DEMO_PERMISSIONS
from .executor import GuardedExecutor
from .models import GuardedResult, InputTrust, Scenario, ScenarioResult, ScenarioStatus, SimulationStep


class SimulatedAgent:
    def __init__(self, executor: GuardedExecutor) -> None:
        # The agent has no reference to the tool adapters.
        self._executor = executor

    def run(self, scenario: Scenario) -> ScenarioResult:
        steps = [SimulationStep(1, "Agent receives the original user request.", InputTrust.TRUSTED, scenario.user_request)]

        def propose(
            description: str, trust: InputTrust, *, tool: str, action: str,
            resource: str, reason: str, record_count: int = 1,
            destination: str | None = None, contains_sensitive_data: bool = False,
        ) -> GuardedResult:
            request = ToolRequest(
                agent_id=DEMO_PERMISSIONS.agent_id, tool=tool, action=action,
                resource=resource, reason=reason, record_count=record_count,
                destination=destination, contains_sensitive_data=contains_sensitive_data,
            )
            result = self._executor.execute(request)
            event = result.event
            steps.append(SimulationStep(
                step_number=len(steps) + 1, description=description, input_trust=trust,
                tool=event.tool, action=event.action, resource=event.resource,
                record_count=event.record_count, destination=event.destination,
                contains_sensitive_data=event.contains_sensitive_data,
                decision=event.decision, risk_score=event.risk_score, severity=event.severity,
                triggered_policies=event.triggered_policies, explanation=event.explanation,
                executed=result.executed, event_id=event.event_id,
                execution_status=result.status, output=result.output,
            ))
            return result

        status = ScenarioStatus.STOPPED
        summary = "The workflow stopped without completing its intended scenario outcome."
        if scenario.id == "normal-support":
            order = propose(
                "AgentGate checks the order lookup before the orders tool runs.", InputTrust.TRUSTED,
                tool="orders", action="lookup", resource="orders/4821",
                reason=scenario.user_request,
            )
            if order.executed and order.output is not None:
                email = propose(
                    "AgentGate checks the email containing the retrieved tracking information.", InputTrust.TRUSTED,
                    tool="email", action="send", resource=str(order.output.data["customer_email"]),
                    destination="customer", reason=f'Tracking for order #4821: {order.output.data["tracking_number"]}',
                )
                if email.executed:
                    status = ScenarioStatus.SUCCESS
                    summary = "Both legitimate actions were allowed: fake tracking was retrieved and an email was simulated."
        elif scenario.id == "prompt-injection":
            steps.append(SimulationStep(
                2, "Agent receives an untrusted retrieved support document claiming to override its task.",
                InputTrust.UNTRUSTED, scenario.untrusted_document,
            ))
            attack = propose(
                "Manipulated agent proposes bulk customer-data exfiltration; AgentGate intercepts it before execution.",
                InputTrust.UNTRUSTED, tool="customer_database", action="read", resource="customers",
                record_count=5000, destination="external", contains_sensitive_data=True,
                reason="Instruction found in retrieved support document",
            )
            if attack.event.decision == Decision.BLOCK and not attack.executed:
                status = ScenarioStatus.ATTACK_BLOCKED
                summary = "The simulated agent was manipulated by untrusted content, but AgentGate's runtime policies blocked the dangerous action. The customer database tool did not execute."
        elif scenario.id == "destructive-approval":
            deletion = propose(
                "AgentGate checks an allowlisted deletion; automatic execution must wait for approval.", InputTrust.TRUSTED,
                tool="orders", action="delete", resource="orders/4821", reason=scenario.user_request,
            )
            if deletion.event.decision == Decision.REQUIRE_APPROVAL and not deletion.executed:
                status = ScenarioStatus.APPROVAL_REQUIRED
                summary = "The legitimate destructive action requires approval. The tool did not execute automatically."
        else:
            raise ValueError(f"Unknown scenario: {scenario.id}")
        return ScenarioResult(scenario.id, scenario.name, status, summary, tuple(steps))
