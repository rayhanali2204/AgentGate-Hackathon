"""Server-owned demo permission configuration shared by API and simulation."""

from .models import AgentPermissions

DEMO_PERMISSIONS = AgentPermissions(
    agent_id="customer-support-agent",
    allowed_tools={"customer_database", "email", "orders"},
    allowed_actions={"read", "lookup", "send", "delete"},
)


def permissions_for(agent_id: str) -> AgentPermissions:
    """Unknown agents get no grants; the engine decides authorization."""
    return DEMO_PERMISSIONS if agent_id == DEMO_PERMISSIONS.agent_id else AgentPermissions(agent_id, set(), set())
