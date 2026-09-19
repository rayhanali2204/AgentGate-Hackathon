"""Compose policy authorization and independent risk assessment."""

from .models import AgentPermissions, Decision, SecurityDecision, ToolRequest
from .policies import evaluate_policies
from .risk import evaluate_risk


def evaluate_request(request: ToolRequest, permissions: AgentPermissions) -> SecurityDecision:
    policies = evaluate_policies(request, permissions)
    outcomes = {policy.decision for policy in policies}
    decision = (
        Decision.BLOCK if Decision.BLOCK in outcomes
        else Decision.REQUIRE_APPROVAL if Decision.REQUIRE_APPROVAL in outcomes
        else Decision.ALLOW
    )
    risk = evaluate_risk(request, permissions)
    authorization = " ".join(policy.explanation for policy in policies) or "Tool and action are permitted; no restrictive policy matched."
    factors = "; ".join(f"{factor.explanation} (+{factor.points})" for factor in risk.factors) or "No risk factors"
    explanation = f"{decision.value}: {authorization} Risk {risk.score}/100 ({risk.severity.value}): {factors}. Scores are capped at 100; policies determine authorization."
    return SecurityDecision(decision, risk.score, risk.severity, policies, explanation)
