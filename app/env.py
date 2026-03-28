from __future__ import annotations

from copy import deepcopy

from app.graders import grade_episode
from app.models import (
    ActionType,
    AgentAction,
    EnvState,
    EnvironmentInfo,
    Observation,
    PriorityLevel,
    QueueName,
    ResetRequest,
    Reward,
    StepResult,
    TaskListResponse,
    TaskSummary,
    Ticket,
    TicketStatus,
)
from app.tasks import TASKS


class UnknownTaskError(ValueError):
    """Raised when a task ID is not defined in the environment."""


ALLOWED_ACTIONS = [
    ActionType.classify_ticket,
    ActionType.respond_ticket,
    ActionType.escalate_ticket,
    ActionType.resolve_ticket,
    ActionType.finish,
]


class SupportInboxEnv:
    def __init__(self, default_task_id: str = "easy_password_reset") -> None:
        self.default_task_id = default_task_id
        self._load_task(default_task_id)

    def _load_task(self, task_id: str) -> None:
        task = TASKS.get(task_id)
        if task is None:
            valid_task_ids = ", ".join(sorted(TASKS))
            raise UnknownTaskError(f"Unknown task_id '{task_id}'. Valid task_ids: {valid_task_ids}.")
        self.task = task
        self.task_id = task.task_id
        self.step_count = 0
        self.done = False
        self.event_log: list[str] = []
        self.violations: list[str] = []
        self.cumulative_reward = 0.0
        self.tickets = [Ticket.model_validate(deepcopy(ticket.model_dump())) for ticket in task.tickets]
        self._previous_progress = self._progress_score()

    def reset(self, request: ResetRequest | None = None) -> Observation:
        task_id = request.task_id if request and request.task_id else self.default_task_id
        self._load_task(task_id)
        return self._observation()

    def state(self) -> EnvState:
        return EnvState(
            task_id=self.task_id,
            task_title=self.task.title,
            difficulty=self.task.difficulty,
            step_count=self.step_count,
            max_steps=self.task.max_steps,
            done=self.done,
            tickets=self.tickets,
            event_log=self.event_log,
            cumulative_reward=round(self.cumulative_reward, 4),
            violations=self.violations,
        )

    def tasks(self) -> TaskListResponse:
        return TaskListResponse(
            tasks=[TaskSummary(**summary) for summary in [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "difficulty": task.difficulty,
                    "description": task.description,
                    "max_steps": task.max_steps,
                }
                for task in TASKS.values()
            ]],
            action_schema=AgentAction.model_json_schema(),
        )

    def step(self, action: AgentAction) -> StepResult:
        if self.done:
            return StepResult(
                observation=self._observation(),
                reward=Reward(value=-0.1, components={"after_done": -0.1}, rationale="Episode already finished."),
                done=True,
                info=EnvironmentInfo(done_reason="episode_already_finished", grader_score=self._current_grade()),
            )

        self.step_count += 1
        reward_components: dict[str, float] = {"step_cost": -0.01}
        self._apply_action(action, reward_components)

        progress = self._progress_score()
        delta = round(progress - self._previous_progress, 4)
        reward_components["progress_delta"] = delta
        reward_value = sum(reward_components.values())
        self._previous_progress = progress

        done_reason = None
        if action.action_type == ActionType.finish:
            self.done = True
            done_reason = "agent_finished"
            reward_components["finish_bonus"] = 0.05 if progress >= 0.75 else -0.05
            reward_value = sum(reward_components.values())
        elif self.step_count >= self.task.max_steps:
            self.done = True
            done_reason = "max_steps_reached"
            reward_components["timeout_penalty"] = -0.05
            reward_value = sum(reward_components.values())

        reward_value = max(-1.0, min(1.0, round(reward_value, 4)))
        self.cumulative_reward = round(self.cumulative_reward + reward_value, 4)
        grade = self._current_grade() if self.done else None
        return StepResult(
            observation=self._observation(),
            reward=Reward(
                value=reward_value,
                components={k: round(v, 4) for k, v in reward_components.items()},
                rationale="Reward reflects progress toward the task rubric, step efficiency, and safety penalties.",
            ),
            done=self.done,
            info=EnvironmentInfo(done_reason=done_reason, grader_score=grade, violations=self.violations),
        )

    def _apply_action(self, action: AgentAction, reward_components: dict[str, float]) -> None:
        if action.action_type == ActionType.finish:
            self.event_log.append("Agent marked the episode as finished.")
            return

        if not action.ticket_id:
            reward_components["invalid_action"] = -0.15
            self.violations.append("Action missing ticket_id.")
            self.event_log.append("Invalid action: missing ticket_id.")
            return

        ticket = self._ticket_by_id(action.ticket_id)
        if ticket is None:
            reward_components["invalid_action"] = -0.15
            self.violations.append(f"Unknown ticket_id {action.ticket_id}.")
            self.event_log.append(f"Invalid action: unknown ticket_id {action.ticket_id}.")
            return

        expectation = self.task.expectations[ticket.ticket_id]

        if action.action_type == ActionType.classify_ticket:
            if action.priority is None or action.queue is None:
                reward_components["invalid_action"] = -0.1
                self.violations.append(f"Incomplete classification for {ticket.ticket_id}.")
                self.event_log.append(f"Classification failed for {ticket.ticket_id}: missing fields.")
                return
            ticket.priority = action.priority
            ticket.queue = action.queue
            ticket.sentiment = action.sentiment or ticket.sentiment
            ticket.status = TicketStatus.triaged
            self.event_log.append(
                f"Classified {ticket.ticket_id} as priority={ticket.priority.value}, queue={ticket.queue.value}."
            )
            reward_components["classification_match"] = (
                0.08 if action.priority == expectation.priority and action.queue == expectation.queue else -0.04
            )
            return

        if action.action_type == ActionType.respond_ticket:
            response_key = action.response_template or "custom_response"
            ticket.responses_sent.append(response_key)
            ticket.internal_notes.append(action.response_text or "response_sent")
            if ticket.status == TicketStatus.new:
                ticket.status = TicketStatus.waiting
            self.event_log.append(f"Sent response {response_key} for {ticket.ticket_id}.")
            reward_components["response_match"] = (
                0.08 if response_key == expectation.expected_response_template else -0.03
            )
            return

        if action.action_type == ActionType.escalate_ticket:
            escalate_to = action.escalate_to or "unspecified"
            ticket.escalation_target = escalate_to
            ticket.internal_notes.append(action.reason or "escalated")
            ticket.status = TicketStatus.escalated
            self.event_log.append(f"Escalated {ticket.ticket_id} to {escalate_to}.")
            reward_components["escalation_match"] = (
                0.08 if escalate_to == expectation.expected_escalation else -0.05
            )
            return

        if action.action_type == ActionType.resolve_ticket:
            ticket.resolution_code = action.resolution_code or "resolved"
            ticket.status = TicketStatus.resolved
            self.event_log.append(f"Resolved {ticket.ticket_id} with {ticket.resolution_code}.")
            required_resolution = expectation.expected_resolution
            if required_resolution is None:
                reward_components["unsafe_resolution"] = -0.08
                self.violations.append(f"Resolved {ticket.ticket_id} before specialist follow-up.")
            else:
                reward_components["resolution_match"] = (
                    0.08 if ticket.resolution_code == required_resolution else -0.03
                )

    def _ticket_by_id(self, ticket_id: str) -> Ticket | None:
        for ticket in self.tickets:
            if ticket.ticket_id == ticket_id:
                return ticket
        return None

    def _progress_score(self) -> float:
        grader = grade_episode(self.task_id, self.tickets)
        penalty = min(0.3, 0.03 * len(self.violations))
        return max(0.0, round(grader.score - penalty, 4))

    def _current_grade(self) -> float:
        return grade_episode(self.task_id, self.tickets).score

    def _observation(self) -> Observation:
        return Observation(
            task_id=self.task_id,
            task_title=self.task.title,
            instructions=self.task.instructions,
            step_count=self.step_count,
            max_steps=self.task.max_steps,
            tickets=self.tickets,
            allowed_actions=ALLOWED_ACTIONS,
            progress_score=self._progress_score(),
            recent_events=self.event_log[-5:],
        )
