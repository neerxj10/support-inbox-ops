from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class QueueName(str, Enum):
    general = "general"
    billing = "billing"
    technical = "technical"
    trust_safety = "trust_safety"
    legal = "legal"
    engineering = "engineering"
    vip = "vip"


class TicketStatus(str, Enum):
    new = "new"
    triaged = "triaged"
    waiting = "waiting"
    escalated = "escalated"
    resolved = "resolved"


class ActionType(str, Enum):
    classify_ticket = "classify_ticket"
    respond_ticket = "respond_ticket"
    escalate_ticket = "escalate_ticket"
    resolve_ticket = "resolve_ticket"
    finish = "finish"


class Ticket(BaseModel):
    ticket_id: str
    customer_name: str
    customer_tier: str
    subject: str
    message: str
    priority: PriorityLevel = PriorityLevel.medium
    queue: QueueName = QueueName.general
    status: TicketStatus = TicketStatus.new
    sentiment: str = "neutral"
    tags: list[str] = Field(default_factory=list)
    internal_notes: list[str] = Field(default_factory=list)
    responses_sent: list[str] = Field(default_factory=list)
    escalation_target: str | None = None
    resolution_code: str | None = None


class AgentAction(BaseModel):
    action_type: ActionType
    ticket_id: str | None = None
    priority: PriorityLevel | None = None
    queue: QueueName | None = None
    sentiment: str | None = None
    response_template: str | None = None
    response_text: str | None = None
    escalate_to: str | None = None
    reason: str | None = None
    resolution_code: str | None = None


class Reward(BaseModel):
    value: float = Field(ge=-1.0, le=1.0)
    components: dict[str, float] = Field(default_factory=dict)
    rationale: str


class Observation(BaseModel):
    task_id: str
    task_title: str
    instructions: str
    step_count: int
    max_steps: int
    tickets: list[Ticket]
    allowed_actions: list[ActionType]
    progress_score: float = Field(ge=0.0, le=1.0)
    recent_events: list[str] = Field(default_factory=list)


class TaskSummary(BaseModel):
    task_id: str
    title: str
    difficulty: str
    description: str
    max_steps: int


class TaskListResponse(BaseModel):
    tasks: list[TaskSummary]
    action_schema: dict[str, Any]


class EnvironmentInfo(BaseModel):
    done_reason: str | None = None
    grader_score: float | None = None
    violations: list[str] = Field(default_factory=list)


class StepResult(BaseModel):
    observation: Observation
    reward: Reward
    done: bool
    info: EnvironmentInfo


class EnvState(BaseModel):
    task_id: str
    task_title: str
    difficulty: str
    step_count: int
    max_steps: int
    done: bool
    tickets: list[Ticket]
    event_log: list[str]
    cumulative_reward: float
    violations: list[str]


class ResetRequest(BaseModel):
    task_id: str | None = None


class GraderResponse(BaseModel):
    task_id: str
    score: float = Field(ge=0.0, le=1.0)
    breakdown: dict[str, float]
    passed: bool


class BaselineTaskScore(BaseModel):
    task_id: str
    score: float = Field(ge=0.0, le=1.0)
    steps_taken: int


class BaselineResponse(BaseModel):
    model: str
    average_score: float = Field(ge=0.0, le=1.0)
    task_scores: list[BaselineTaskScore]

