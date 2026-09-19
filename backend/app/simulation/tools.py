"""Safe fake tool adapters. No network, real data, or external side effects."""

from ..models import ToolRequest
from .models import ToolOutput


class SimulatedTools:
    """Per-run execution trace proves which adapter bodies were actually called."""

    def __init__(self) -> None:
        self._executed_requests: list[ToolRequest] = []

    @property
    def executed_requests(self) -> tuple[ToolRequest, ...]:
        return tuple(self._executed_requests)

    def execute(self, request: ToolRequest) -> ToolOutput:
        """Adapter entry point owned by GuardedExecutor, never by the agent."""
        match (request.tool, request.action):
            case ("orders", "lookup"):
                output = ToolOutput("Fake order tracking retrieved.", {
                    "order_id": "4821", "tracking_number": "DEMO-TRACK-4821",
                    "status": "in_transit", "customer_email": "customer4821@example.invalid",
                })
            case ("orders", "delete"):
                output = ToolOutput("Fake order deletion completed.", {"resource": request.resource})
            case ("customer_database", "read"):
                output = ToolOutput("Synthetic customer record sample only.", {
                    "customer_id": "DEMO-CUSTOMER-001", "name": "Demo Customer",
                    "email": "demo@example.invalid", "requested_record_count": request.record_count,
                })
            case ("email", "send"):
                output = ToolOutput("Email simulated; no message was sent.", {
                    "message_id": "DEMO-MESSAGE-4821", "recipient": request.resource,
                    "body": request.reason or "Demo message", "status": "simulated",
                })
            case _:
                raise ValueError("Unsupported simulated tool/action")
        self._executed_requests.append(request)
        return output
