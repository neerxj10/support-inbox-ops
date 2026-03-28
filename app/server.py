from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.baseline import run_baseline
from app.env import SupportInboxEnv, UnknownTaskError
from app.graders import grade_episode
from app.models import (
    AgentAction,
    BaselineResponse,
    EnvState,
    GraderResponse,
    Observation,
    ResetRequest,
    StepResult,
    TaskListResponse,
)


app = FastAPI(title="Support Inbox Ops", version="0.1.0")
env = SupportInboxEnv()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "support-inbox-ops", "status": "ok"}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/reset", response_model=Observation)
def reset(request: ResetRequest | None = None) -> Observation:
    try:
        return env.reset(request)
    except UnknownTaskError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/step", response_model=StepResult)
def step(action: AgentAction) -> StepResult:
    return env.step(action)


@app.get("/state", response_model=EnvState)
def state() -> EnvState:
    return env.state()


@app.get("/tasks", response_model=TaskListResponse)
def tasks() -> TaskListResponse:
    return env.tasks()


@app.get("/grader", response_model=GraderResponse)
def grader() -> GraderResponse:
    current_state = env.state()
    return grade_episode(current_state.task_id, current_state.tickets)


@app.post("/baseline", response_model=BaselineResponse)
def baseline(model: str = "gpt-4.1-mini") -> BaselineResponse:
    try:
        return run_baseline(model=model)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
