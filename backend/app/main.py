"""FastAPI application factory and local development entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.simulation_routes import router as simulation_router
from .events import InMemorySecurityEventStore, SecurityEventStore


def create_app(event_store: SecurityEventStore | None = None) -> FastAPI:
    application = FastAPI(
        title="AgentGate API",
        version="0.2.0",
        description="Zero-trust runtime security gateway for autonomous AI agents.",
    )
    application.state.event_store = event_store if event_store is not None else InMemorySecurityEventStore()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)
    application.include_router(simulation_router)
    return application


app = create_app()
