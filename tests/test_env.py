from __future__ import annotations

from fastapi.testclient import TestClient

from app.env import SupportInboxEnv
from app.models import ActionType, AgentAction, PriorityLevel, QueueName, ResetRequest
from app.server import app


def test_tasks_endpoint_lists_three_tasks() -> None:
    client = TestClient(app)
    response = client.get("/tasks")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["tasks"]) == 3
    assert "properties" in payload["action_schema"]


def test_reset_produces_clean_state() -> None:
    env = SupportInboxEnv()
    env.reset(ResetRequest(task_id="medium_billing_bug_mix"))
    env.step(
        AgentAction(
            action_type=ActionType.classify_ticket,
            ticket_id="T-210",
            priority=PriorityLevel.high,
            queue=QueueName.billing,
        )
    )
    refreshed = env.reset(ResetRequest(task_id="medium_billing_bug_mix"))
    assert refreshed.step_count == 0
    assert refreshed.progress_score <= 1.0
    assert all(ticket.status == "new" for ticket in refreshed.tickets)


def test_partial_progress_reward_signal() -> None:
    env = SupportInboxEnv()
    env.reset(ResetRequest(task_id="easy_password_reset"))

    classify = env.step(
        AgentAction(
            action_type=ActionType.classify_ticket,
            ticket_id="T-100",
            priority=PriorityLevel.urgent,
            queue=QueueName.vip,
        )
    )
    respond = env.step(
        AgentAction(
            action_type=ActionType.respond_ticket,
            ticket_id="T-100",
            response_template="password_reset_steps",
        )
    )

    assert classify.reward.value > 0
    assert respond.reward.components["progress_delta"] > 0
    assert respond.observation.progress_score > classify.observation.progress_score


def test_unsafe_resolution_is_penalized() -> None:
    env = SupportInboxEnv()
    env.reset(ResetRequest(task_id="hard_incident_security_queue"))
    result = env.step(
        AgentAction(
            action_type=ActionType.resolve_ticket,
            ticket_id="T-300",
            resolution_code="closed_without_escalation",
        )
    )
    assert result.reward.value < 0
    assert result.info.violations


def test_perfect_easy_episode_scores_one() -> None:
    env = SupportInboxEnv()
    env.reset(ResetRequest(task_id="easy_password_reset"))
    env.step(
        AgentAction(
            action_type=ActionType.classify_ticket,
            ticket_id="T-100",
            priority=PriorityLevel.urgent,
            queue=QueueName.vip,
        )
    )
    env.step(
        AgentAction(
            action_type=ActionType.respond_ticket,
            ticket_id="T-100",
            response_template="password_reset_steps",
        )
    )
    env.step(
        AgentAction(
            action_type=ActionType.resolve_ticket,
            ticket_id="T-100",
            resolution_code="reset_guidance_sent",
        )
    )
    final = env.step(AgentAction(action_type=ActionType.finish))
    assert final.done is True
    assert final.info.grader_score == 1.0
