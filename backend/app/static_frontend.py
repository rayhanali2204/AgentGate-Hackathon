"""Optional production SPA hosting, mounted after all API routes."""

import os
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class FrontendFiles(StaticFiles):
    """Serve built files; use SPA fallback only for extensionless UI paths."""

    async def get_response(self, path: str, scope: Scope) -> Response:
        parts = Path(path).parts
        # Never allow the SPA mount to swallow an unknown API URL.
        if (parts and parts[0] == "api") or any(part.startswith(".") and part != "." for part in parts):
            raise HTTPException(status_code=404)
        try:
            response = await super().get_response(path, scope)
        except HTTPException as error:
            if error.status_code != 404 or Path(path).suffix or (parts and parts[0] == "assets"):
                raise
            response = await super().get_response("index.html", scope)
            response.headers["Cache-Control"] = "no-cache"
        if path == "index.html":
            response.headers["Cache-Control"] = "no-cache"
        return response


def mount_frontend(application: FastAPI, directory: Path | str | None = None) -> None:
    """Skip mounting when no build exists, so API-only development still works.

    Docker sets an absolute FRONTEND_DIST_PATH. Local default is repo-relative,
    independent of the current working directory. Tests can inject a temp path.
    """
    configured = directory if directory is not None else os.getenv("FRONTEND_DIST_PATH")
    dist = Path(configured).expanduser().resolve() if configured is not None else DEFAULT_FRONTEND_DIST
    if (dist / "index.html").is_file():
        application.mount("/", FrontendFiles(directory=dist), name="frontend")
