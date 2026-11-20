"""Local-first loopback HTTP server entrypoint for SYNAPSE API."""

from __future__ import annotations

import uvicorn

from synapse_api.app import create_app
from synapse_api.config import Settings


def main() -> int:
    settings = Settings.from_env()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.bind_host,
        port=settings.bind_port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
