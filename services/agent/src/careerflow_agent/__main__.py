from __future__ import annotations

import json

import uvicorn

from .api import create_app
from .config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.local_token.get_secret_value():
        raise SystemExit("CAREERFLOW_LOCAL_TOKEN is required")
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    print(
        json.dumps(
            {
                "type": "service_starting",
                "host": settings.host,
                "port": settings.port,
            }
        ),
        flush=True,
    )
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        access_log=False,
    )


if __name__ == "__main__":
    main()
