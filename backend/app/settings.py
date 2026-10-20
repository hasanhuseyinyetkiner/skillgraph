"""Runtime configuration."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "demo"
    database_url: str = "sqlite:///./data/skillgraph.db"
    host: str = "127.0.0.1"
    port: int = 8105
    allow_network_bind: bool = False
    auto_seed: bool = True
    run_migrations: bool = True
    embeddings_enabled: bool = False
    cors_origins: str = "http://127.0.0.1:5105,http://localhost:5105"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


def assert_bind_allowed(host: str, allow_network_bind: bool) -> None:
    """Refuse a non-loopback bind unless the operator opts in."""

    if host not in LOOPBACK_HOSTS and not allow_network_bind:
        raise SystemExit(
            f"Refusing to bind non-loopback host {host!r}. "
            "Set ALLOW_NETWORK_BIND=true to override."
        )
