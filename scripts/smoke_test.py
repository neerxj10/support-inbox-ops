from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.server import app


def main() -> None:
    client = TestClient(app)

    reset_response = client.post("/reset", json={"task_id": "easy_password_reset"})
    assert reset_response.status_code == 200, reset_response.text
    observation = reset_response.json()
    assert observation["task_id"] == "easy_password_reset"

    step_response = client.post(
        "/step",
        json={
            "action_type": "classify_ticket",
            "ticket_id": "T-100",
            "priority": "urgent",
            "queue": "vip",
            "sentiment": "frustrated",
        },
    )
    assert step_response.status_code == 200, step_response.text

    state_response = client.get("/state")
    assert state_response.status_code == 200, state_response.text

    tasks_response = client.get("/tasks")
    assert tasks_response.status_code == 200, tasks_response.text
    assert len(tasks_response.json()["tasks"]) >= 3

    grader_response = client.get("/grader")
    assert grader_response.status_code == 200, grader_response.text
    assert 0.0 <= grader_response.json()["score"] <= 1.0

    print("Smoke test passed.")


if __name__ == "__main__":
    main()
