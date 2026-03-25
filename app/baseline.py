from __future__ import annotations

import argparse
import json
import os
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.env import SupportInboxEnv
from app.models import AgentAction, BaselineResponse, BaselineTaskScore, ResetRequest
from app.tasks import TASKS


SYSTEM_PROMPT = """
You are operating a deterministic customer-support triage simulator.
Return exactly one JSON object with keys that match the action schema.
Choose from action_type: classify_ticket, respond_ticket, escalate_ticket, resolve_ticket, finish.
Use only ticket IDs visible in the observation.
Be concise and policy-safe: do not close specialist tickets prematurely.
""".strip()


def _build_user_prompt(observation: dict[str, Any]) -> str:
    return (
        "Observation JSON:\n"
        f"{json.dumps(observation, indent=2)}\n\n"
        "Choose the single best next action. Output only JSON."
    )


def run_baseline(model: str = "gpt-4.1-mini") -> BaselineResponse:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required to run the baseline.")

    client = OpenAI(api_key=api_key)
    env = SupportInboxEnv()
    task_scores: list[BaselineTaskScore] = []

    for task_id in TASKS:
        observation = env.reset(ResetRequest(task_id=task_id))
        done = False
        result = None
        while not done:
            response = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": _build_user_prompt(observation.model_dump(mode="json"))},
                ],
            )
            try:
                action_payload = json.loads(response.choices[0].message.content or "{}")
                action = AgentAction.model_validate(action_payload)
            except (json.JSONDecodeError, ValidationError):
                action = AgentAction(action_type="finish")
            result = env.step(action)
            observation = result.observation
            done = result.done

        if result is None:
            raise RuntimeError(f"Baseline failed to produce any result for task {task_id}.")
        score = result.info.grader_score or 0.0
        task_scores.append(BaselineTaskScore(task_id=task_id, score=round(score, 4), steps_taken=env.step_count))

    average_score = round(sum(item.score for item in task_scores) / len(task_scores), 4)
    return BaselineResponse(model=model, average_score=average_score, task_scores=task_scores)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenEnv baseline against all tasks.")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    args = parser.parse_args()
    result = run_baseline(model=args.model)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
