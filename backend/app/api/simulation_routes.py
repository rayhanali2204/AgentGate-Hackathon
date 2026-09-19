"""Scenario endpoints share the existing injected security event store."""

from fastapi import APIRouter, HTTPException

from ..permissions import DEMO_PERMISSIONS
from ..simulation.agent import SimulatedAgent
from ..simulation.executor import GuardedExecutor
from ..simulation.scenarios import SCENARIOS, get_scenario
from ..simulation.tools import SimulatedTools
from .routes import StoreDependency
from .simulation_schemas import ScenarioResultSchema, ScenarioSchema

router = APIRouter(prefix="/api/scenarios", tags=["simulation"])


@router.get("", response_model=list[ScenarioSchema])
def list_scenarios() -> list[ScenarioSchema]:
    return [ScenarioSchema.model_validate(scenario) for scenario in SCENARIOS]


@router.post("/{scenario_id}/run", response_model=ScenarioResultSchema)
def run_scenario(scenario_id: str, store: StoreDependency) -> ScenarioResultSchema:
    scenario = get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    executor = GuardedExecutor(DEMO_PERMISSIONS, store, SimulatedTools())
    return ScenarioResultSchema.model_validate(SimulatedAgent(executor).run(scenario))
