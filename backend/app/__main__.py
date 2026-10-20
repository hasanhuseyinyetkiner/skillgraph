"""Loopback-by-default API entrypoint."""

import uvicorn

from app.main import app
from app.settings import assert_bind_allowed


def main() -> None:
    settings = app.state.settings
    assert_bind_allowed(settings.host, settings.allow_network_bind)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
