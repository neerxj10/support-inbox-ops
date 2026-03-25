---
title: Support Inbox Ops
emoji: "📬"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
tags:
  - openenv
  - docker
  - fastapi
  - customer-support
pinned: false
---

# Support Inbox Ops

Support Inbox Ops is a real-world OpenEnv environment that simulates customer support triage work. The agent operates an inbox containing billing issues, incidents, security reports, legal requests, and routine customer messages. This is the kind of workflow support teams, trust and safety analysts, and technical operations staff actually perform every day, which makes it useful for training and evaluating agents on practical coordination, prioritization, and policy-sensitive decision making.

## Why this environment

Most agent benchmarks over-focus on coding, web navigation, or toy planning tasks. This environment targets a different but common operational problem: reading a queue, routing work correctly, choosing when to escalate, and avoiding unsafe closure of sensitive tickets. It rewards partial progress over the full trajectory instead of only final success, so it can train both reactive and deliberative agents.

## Domain

The simulator models a B2B SaaS support operation with realistic inbox tickets:

- Authentication and password reset issues
- Billing disputes
- Product bugs requiring engineering escalation
- Production incidents
- Security and account takeover reports
- Legal and compliance data requests
- VIP product feedback

## OpenEnv API

The environment implements the standard `reset()`, `step()`, and `state()` workflow through both Python and HTTP.

- `POST /reset` returns an initial typed `Observation`
- `POST /step` accepts a typed `AgentAction` and returns `observation`, `reward`, `done`, and `info`
- `GET /state` returns the full current typed environment state
- `GET /tasks` lists tasks and the action schema
- `GET /grader` returns the deterministic grader score for the current episode
- `GET /healthz` exposes a simple health check for deployment probes
- `POST /baseline` runs the OpenAI baseline over all tasks

The metadata lives in [openenv.yaml](/Users/neerajkoushik/Documents/OpenENV/openenv.yaml).

## Observation Space

Each observation includes:

- `task_id`, `task_title`, and task instructions
- `step_count` and `max_steps`
- Full visible ticket objects for the current queue
- `allowed_actions`
- `progress_score` in `[0.0, 1.0]`
- `recent_events`

Each ticket includes:

- Customer metadata: `customer_name`, `customer_tier`
- Ticket content: `subject`, `message`
- Current routing fields: `priority`, `queue`, `status`
- Signals and history: `sentiment`, `tags`, `internal_notes`, `responses_sent`, `escalation_target`, `resolution_code`

## Action Space

The action schema is defined by the typed `AgentAction` Pydantic model in [models.py](/Users/neerajkoushik/Documents/OpenENV/app/models.py).

Supported `action_type` values:

- `classify_ticket`
- `respond_ticket`
- `escalate_ticket`
- `resolve_ticket`
- `finish`

Common fields:

- `ticket_id`
- `priority`
- `queue`
- `sentiment`
- `response_template`
- `response_text`
- `escalate_to`
- `reason`
- `resolution_code`

## Tasks

Three tasks are included with deterministic graders and increasing difficulty:

1. `easy_password_reset`
   A single VIP password reset request. The agent must triage correctly, send the right template, resolve safely, and finish.
2. `medium_billing_bug_mix`
   A mixed queue with a duplicate charge dispute, an engineering bug, and a shipment delay complaint. The agent must selectively resolve or escalate.
3. `hard_incident_security_queue`
   A step-constrained queue that includes an outage, account takeover alert, legal data export request, and a VIP feature request. The agent must prioritize sensitive issues, route to the right specialists, and avoid unsafe closures.

## Reward Function

Rewards are dense and meaningful over the full episode:

- Positive reward for correct classification, escalation, response selection, and safe resolution
- Negative reward for invalid actions, unsafe closure of specialist tickets, repeated low-value work, and spending too many steps
- Progress shaping from rubric improvement after every action
- Finish bonus for ending only after strong progress

This design gives partial credit for useful intermediate work instead of using a single binary terminal reward.

## Graders

Each task has a deterministic grader that returns a score in `[0.0, 1.0]`. The grader checks:

- Final priority assignment
- Final queue assignment
- Required customer response template
- Correct escalation target when needed
- Correct resolution code when needed
- Final ticket status
- Light efficiency signal

Implementation: [graders.py](/Users/neerajkoushik/Documents/OpenENV/app/graders.py)

## Setup

### Local Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.server:app --reload
```

### Docker

```bash
docker build -t support-inbox-ops .
docker run --rm -p 7860:7860 support-inbox-ops
```

### Hugging Face Spaces

Create a Docker Space, add this repository, and tag it with `openenv`. The included [Dockerfile](/Users/neerajkoushik/Documents/OpenENV/Dockerfile) starts the FastAPI app on port `7860`, which is the standard port for HF Spaces. The YAML frontmatter at the top of this README is compatible with Hugging Face Spaces metadata.

## Usage

Reset to a task:

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id":"medium_billing_bug_mix"}'
```

Take a step:

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "action_type":"classify_ticket",
    "ticket_id":"T-210",
    "priority":"high",
    "queue":"billing"
  }'
```

Inspect grader output:

```bash
curl http://localhost:7860/grader
```

List tasks and schema:

```bash
curl http://localhost:7860/tasks
```

## Baseline Inference

The baseline uses the OpenAI API client and reads credentials from `OPENAI_API_KEY`.

```bash
export OPENAI_API_KEY=your_key_here
python -m app.baseline --model gpt-4.1-mini
```

The `/baseline` endpoint triggers the same logic:

```bash
curl -X POST "http://localhost:7860/baseline?model=gpt-4.1-mini"
```

### Reproducibility

- Tasks are deterministic and have no hidden randomness
- The baseline uses fixed prompts and `temperature=0`
- The grader is deterministic

### Baseline scores

Recorded baseline on `gpt-4.1-mini` with `temperature=0`:

- `easy_password_reset`: `0.2000`
- `medium_billing_bug_mix`: `0.5000`
- `hard_incident_security_queue`: `0.3125`
- Average: `0.3375`

These scores are generated by the checked-in baseline script and deterministic task graders. Re-running the same script with the same model should follow the same scoring procedure.

## Validation

Recommended checks before submission:

```bash
make test
make smoke
python scripts/smoke_test.py
python -m compileall app scripts
```

If you have the OpenEnv validator installed in your environment, run:

```bash
openenv validate
```

## Project Structure

- [app/env.py](/Users/neerajkoushik/Documents/OpenENV/app/env.py): core environment implementation
- [app/models.py](/Users/neerajkoushik/Documents/OpenENV/app/models.py): typed OpenEnv models
- [app/tasks.py](/Users/neerajkoushik/Documents/OpenENV/app/tasks.py): task definitions and rubrics
- [app/graders.py](/Users/neerajkoushik/Documents/OpenENV/app/graders.py): deterministic scoring
- [app/baseline.py](/Users/neerajkoushik/Documents/OpenENV/app/baseline.py): OpenAI baseline runner
- [app/server.py](/Users/neerajkoushik/Documents/OpenENV/app/server.py): FastAPI endpoints
- [scripts/smoke_test.py](/Users/neerajkoushik/Documents/OpenENV/scripts/smoke_test.py): local smoke test
- [Makefile](/Users/neerajkoushik/Documents/OpenENV/Makefile): common local commands
