"""Start the বই বন্ধু API.

    python -m backend.app          # or: python backend/run.py

The first start loads multilingual-e5-large (about 20s); after that the model stays
resident and each question only pays for retrieval plus generation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

# Allow "python backend/run.py" from the project root as well as "python -m backend.run".
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HOST = "127.0.0.1"
PORT = 8000


def main() -> None:
    uvicorn.run("backend.app:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
