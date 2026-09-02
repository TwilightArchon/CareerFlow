from __future__ import annotations

import json
from pathlib import Path

from careerflow_agent.api import create_app
from careerflow_agent.config import Settings


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    app = create_app(Settings(local_token="schema-export-token-value-32-chars"))
    target = root / "packages" / "contracts" / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
