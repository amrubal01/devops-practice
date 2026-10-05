"""
Log Filter Service
-------------------
A small FastAPI service that mimics a simplified version of a log
ingestion/filtering pipeline: you POST raw log lines in, optionally
filter by severity level, and retrieve the filtered results back out.

This is intentionally simple — the point of this project is the
surrounding DevOps tooling (CI/CD, Docker, Kubernetes, supply chain
security), not the app logic itself.
"""

from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Log Filter Service",
    description="A minimal service for ingesting and filtering log entries.",
    version="0.1.0",
    # Explicit (these are the defaults, but spelling them out so it's
    # obvious where to change them, e.g. to disable docs in production
    # by setting docs_url=None).
    docs_url="/docs",       # Swagger UI
    redoc_url="/redoc",     # ReDoc, FastAPI's other built-in docs UI
    openapi_url="/openapi.json",
)

# In-memory store. Fine for a demo/portfolio project — swap for a real
# datastore (Postgres, Redis, etc.) if you want to extend this later.
_LOG_STORE: dict[str, "LogEntry"] = {}

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LogEntryIn(BaseModel):
    source: str = Field(..., description="System or service that produced the log line")
    level: str = Field(..., description="Log severity level")
    message: str = Field(..., description="Raw log message text")


class LogEntry(LogEntryIn):
    id: str


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the bare root path to Swagger UI for convenience."""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["ops"])
def health() -> dict:
    """Liveness/readiness check. Used by Docker/Kubernetes health probes."""
    return {"status": "ok"}


@app.post("/logs", response_model=LogEntry, status_code=201, tags=["logs"])
def ingest_log(entry: LogEntryIn) -> LogEntry:
    """Ingest a single raw log entry."""
    level = entry.level.upper()
    if level not in VALID_LEVELS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid level '{entry.level}'. Must be one of {sorted(VALID_LEVELS)}.",
        )
    log_id = str(uuid4())
    stored = LogEntry(id=log_id, source=entry.source, level=level, message=entry.message)
    _LOG_STORE[log_id] = stored
    return stored


@app.get("/logs", response_model=List[LogEntry], tags=["logs"])
def list_logs(level: Optional[str] = None, source: Optional[str] = None) -> List[LogEntry]:
    """
    List stored logs, optionally filtered by level and/or source.

    Example: GET /logs?level=ERROR&source=cisco-switch-01
    """
    results = list(_LOG_STORE.values())

    if level is not None:
        level_upper = level.upper()
        if level_upper not in VALID_LEVELS:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid level '{level}'. Must be one of {sorted(VALID_LEVELS)}.",
            )
        results = [entry for entry in results if entry.level == level_upper]

    if source is not None:
        results = [entry for entry in results if entry.source == source]

    return results


@app.get("/logs/{log_id}", response_model=LogEntry, tags=["logs"])
def get_log(log_id: str) -> LogEntry:
    """Fetch a single log entry by id."""
    entry = _LOG_STORE.get(log_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Log entry not found")
    return entry


@app.delete("/logs/{log_id}", status_code=204, tags=["logs"])
def delete_log(log_id: str) -> None:
    """Delete a single log entry by id."""
    if log_id not in _LOG_STORE:
        raise HTTPException(status_code=404, detail="Log entry not found")
    del _LOG_STORE[log_id]
