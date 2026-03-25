from __future__ import annotations

from app.models import GraderResponse, TicketStatus
from app.tasks import TASKS, TaskDefinition


def _score_ticket(task: TaskDefinition, ticket_id: str, ticket) -> tuple[float, dict[str, float]]:
    expectation = task.expectations[ticket_id]
    components: dict[str, float] = {}

    components["priority"] = 1.0 if ticket.priority == expectation.priority else 0.0
    components["queue"] = 1.0 if ticket.queue == expectation.queue else 0.0

    response_ok = (
        expectation.expected_response_template is None
        or expectation.expected_response_template in ticket.responses_sent
    )
    components["response"] = 1.0 if response_ok else 0.0

    escalation_ok = (
        expectation.expected_escalation is None
        or ticket.escalation_target == expectation.expected_escalation
    )
    components["escalation"] = 1.0 if escalation_ok else 0.0

    resolution_ok = (
        expectation.expected_resolution is None
        or ticket.resolution_code == expectation.expected_resolution
    )
    components["resolution"] = 1.0 if resolution_ok else 0.0

    required_status = expectation.expected_resolution is not None
    if required_status:
        components["status"] = 1.0 if ticket.status == TicketStatus.resolved else 0.0
    else:
        components["status"] = 1.0 if ticket.status != TicketStatus.resolved else 0.5

    expected_notes = sum(1 for action in expectation.required_actions if action in {"respond_ticket", "escalate_ticket"})
    extra_notes = max(0, len(ticket.internal_notes) - expected_notes)
    components["efficiency"] = max(0.0, 1.0 - (extra_notes / 3))

    weights = {
        "priority": 0.15,
        "queue": 0.2,
        "response": 0.2,
        "escalation": 0.15,
        "resolution": 0.15,
        "status": 0.1,
        "efficiency": 0.05,
    }
    total = sum(components[name] * weight for name, weight in weights.items())
    return total, components


def grade_episode(task_id: str, tickets: list) -> GraderResponse:
    task = TASKS[task_id]
    by_id = {ticket.ticket_id: ticket for ticket in tickets}

    breakdown: dict[str, float] = {}
    ticket_scores: list[float] = []
    for ticket_id in task.expectations:
        score, components = _score_ticket(task, ticket_id, by_id[ticket_id])
        breakdown[ticket_id] = round(score, 4)
        for name, value in components.items():
            breakdown[f"{ticket_id}.{name}"] = round(value, 4)
        ticket_scores.append(score)

    final_score = round(sum(ticket_scores) / len(ticket_scores), 4)
    return GraderResponse(
        task_id=task_id,
        score=final_score,
        breakdown=breakdown,
        passed=final_score >= 0.8,
    )
