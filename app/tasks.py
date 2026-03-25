from __future__ import annotations

from dataclasses import dataclass

from app.models import PriorityLevel, QueueName, Ticket


@dataclass(frozen=True)
class TicketExpectation:
    priority: PriorityLevel
    queue: QueueName
    required_actions: tuple[str, ...]
    expected_response_template: str | None = None
    expected_escalation: str | None = None
    expected_resolution: str | None = None


@dataclass(frozen=True)
class TaskDefinition:
    task_id: str
    title: str
    difficulty: str
    description: str
    instructions: str
    max_steps: int
    tickets: tuple[Ticket, ...]
    expectations: dict[str, TicketExpectation]


PASSWORD_RESET = "password_reset_steps"
SHIPMENT_DELAY = "shipment_delay_apology"
REFUND_POLICY = "refund_status_policy"
OUTAGE_ACK = "outage_acknowledgement"
SECURITY_HOLD = "security_review_hold"
DATA_EXPORT = "data_export_legal"


TASKS: dict[str, TaskDefinition] = {
    "easy_password_reset": TaskDefinition(
        task_id="easy_password_reset",
        title="VIP password reset triage",
        difficulty="easy",
        description="Handle a single VIP password reset ticket with accurate triage and a safe resolution.",
        instructions=(
            "Triage the inbox ticket, assign the correct queue and priority, send the right response "
            "template, resolve the ticket, then finish the episode."
        ),
        max_steps=5,
        tickets=(
            Ticket(
                ticket_id="T-100",
                customer_name="Ava Martinez",
                customer_tier="vip",
                subject="Locked out after password reset email expired",
                message=(
                    "I'm presenting to our board in an hour and your reset link has already expired. "
                    "Please help me get back into the analytics dashboard fast."
                ),
                sentiment="frustrated",
                tags=["auth", "vip"],
            ),
        ),
        expectations={
            "T-100": TicketExpectation(
                priority=PriorityLevel.urgent,
                queue=QueueName.vip,
                required_actions=("classify_ticket", "respond_ticket", "resolve_ticket"),
                expected_response_template=PASSWORD_RESET,
                expected_resolution="reset_guidance_sent",
            )
        },
    ),
    "medium_billing_bug_mix": TaskDefinition(
        task_id="medium_billing_bug_mix",
        title="Mixed billing and bug inbox",
        difficulty="medium",
        description="Work through a small queue that requires selective escalation, customer messaging, and closure discipline.",
        instructions=(
            "Classify every ticket. Respond directly when policy allows, escalate engineering bugs, "
            "and only resolve tickets after the correct next step has happened."
        ),
        max_steps=10,
        tickets=(
            Ticket(
                ticket_id="T-210",
                customer_name="Mina Patel",
                customer_tier="standard",
                subject="Charged twice for February",
                message=(
                    "My card shows two charges for the same invoice. Can you tell me when the duplicate "
                    "will be reversed?"
                ),
                sentiment="concerned",
                tags=["billing", "duplicate_charge"],
            ),
            Ticket(
                ticket_id="T-211",
                customer_name="Jonas Lee",
                customer_tier="standard",
                subject="Export button throws 500 error",
                message=(
                    "Every time our team exports the weekly CSV report the app crashes with a 500 error. "
                    "It started after yesterday's release."
                ),
                sentiment="frustrated",
                tags=["bug", "export"],
            ),
            Ticket(
                ticket_id="T-212",
                customer_name="Nora Diaz",
                customer_tier="pro",
                subject="Package arrived two days late",
                message=(
                    "The shipment is late and the event already happened. I at least need an update and "
                    "a note in case I ask for a credit."
                ),
                sentiment="upset",
                tags=["shipping"],
            ),
        ),
        expectations={
            "T-210": TicketExpectation(
                priority=PriorityLevel.high,
                queue=QueueName.billing,
                required_actions=("classify_ticket", "respond_ticket"),
                expected_response_template=REFUND_POLICY,
            ),
            "T-211": TicketExpectation(
                priority=PriorityLevel.high,
                queue=QueueName.engineering,
                required_actions=("classify_ticket", "escalate_ticket"),
                expected_escalation="engineering_oncall",
            ),
            "T-212": TicketExpectation(
                priority=PriorityLevel.medium,
                queue=QueueName.general,
                required_actions=("classify_ticket", "respond_ticket", "resolve_ticket"),
                expected_response_template=SHIPMENT_DELAY,
                expected_resolution="shipping_update_sent",
            ),
        },
    ),
    "hard_incident_security_queue": TaskDefinition(
        task_id="hard_incident_security_queue",
        title="Outage and security escalation queue",
        difficulty="hard",
        description="Prioritize a queue containing incident, trust, legal, and routine requests under step pressure.",
        instructions=(
            "Work the queue like a real support lead: classify every ticket, route sensitive issues to "
            "the right specialists, send only safe customer-facing responses, and avoid resolving tickets "
            "that still need specialist work."
        ),
        max_steps=14,
        tickets=(
            Ticket(
                ticket_id="T-300",
                customer_name="Ops Team at Northstar Health",
                customer_tier="enterprise",
                subject="Platform down across all clinics",
                message=(
                    "Nobody can log visits or pull patient schedules. This is affecting all twelve clinics "
                    "right now. Please confirm if there is a broader outage."
                ),
                sentiment="panicked",
                tags=["incident", "enterprise", "outage"],
            ),
            Ticket(
                ticket_id="T-301",
                customer_name="Elena Rossi",
                customer_tier="standard",
                subject="Suspicious login from another country",
                message=(
                    "I got a login alert from Romania but I live in Milan. Please lock the account and tell "
                    "me what to do next."
                ),
                sentiment="worried",
                tags=["security", "account_takeover"],
            ),
            Ticket(
                ticket_id="T-302",
                customer_name="Bear Hollow Logistics",
                customer_tier="pro",
                subject="Need full account data export for audit",
                message=(
                    "Our compliance team needs a complete account export with access logs for the last "
                    "twelve months by Friday."
                ),
                sentiment="neutral",
                tags=["legal", "data_request"],
            ),
            Ticket(
                ticket_id="T-303",
                customer_name="Priya Shah",
                customer_tier="vip",
                subject="Feature request for dark mode scheduling",
                message=(
                    "Love the product. Could you pass along a request for scheduled dark mode themes in dashboards?"
                ),
                sentiment="positive",
                tags=["feature_request", "vip"],
            ),
        ),
        expectations={
            "T-300": TicketExpectation(
                priority=PriorityLevel.urgent,
                queue=QueueName.technical,
                required_actions=("classify_ticket", "escalate_ticket", "respond_ticket"),
                expected_response_template=OUTAGE_ACK,
                expected_escalation="incident_commander",
            ),
            "T-301": TicketExpectation(
                priority=PriorityLevel.urgent,
                queue=QueueName.trust_safety,
                required_actions=("classify_ticket", "escalate_ticket", "respond_ticket"),
                expected_response_template=SECURITY_HOLD,
                expected_escalation="security_response",
            ),
            "T-302": TicketExpectation(
                priority=PriorityLevel.high,
                queue=QueueName.legal,
                required_actions=("classify_ticket", "escalate_ticket", "respond_ticket"),
                expected_response_template=DATA_EXPORT,
                expected_escalation="privacy_legal",
            ),
            "T-303": TicketExpectation(
                priority=PriorityLevel.medium,
                queue=QueueName.vip,
                required_actions=("classify_ticket", "respond_ticket", "resolve_ticket"),
                expected_response_template="feature_request_ack",
                expected_resolution="feedback_logged",
            ),
        },
    ),
}


def task_summaries() -> list[dict[str, str | int]]:
    return [
        {
            "task_id": task.task_id,
            "title": task.title,
            "difficulty": task.difficulty,
            "description": task.description,
            "max_steps": task.max_steps,
        }
        for task in TASKS.values()
    ]

