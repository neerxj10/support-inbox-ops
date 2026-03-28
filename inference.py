from __future__ import annotations

import os

import uvicorn

from app.server import app


def main() -> None:
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run("inference:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
