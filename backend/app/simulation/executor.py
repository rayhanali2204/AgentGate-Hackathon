"""The simulation's single guarded path from proposed action to fake tool."""

from ..evaluation import evaluate_and_record
from ..events import SecurityEventStore
from ..models import AgentPermissions, Decision, ToolRequest
from .models import ExecutionStatus, GuardedResult
from .tools import SimulatedTools


class GuardedExecutor:
    def __init__(self, permissions: AgentPermissions, store: SecurityEventStore, tools: SimulatedTools) -> None:
        self._permissions = permissions
        self._store = store
        self._tools = tools

    def execute(self, request: ToolRequest) -> GuardedResult:
        event = evaluate_and_record(request, self._permissions, self._store)
        if event.decision == Decision.ALLOW:
            output = self._tools.execute(request)
            return GuardedResult(ExecutionStatus.EXECUTED, event, True, output)
        status = ExecutionStatus.BLOCKED if event.decision == Decision.BLOCK else ExecutionStatus.PENDING_APPROVAL
        return GuardedResult(status, event, False)
