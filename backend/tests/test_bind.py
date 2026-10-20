import pytest
from app.settings import assert_bind_allowed


def test_loopback_is_allowed_and_public_bind_is_refused() -> None:
    assert_bind_allowed("127.0.0.1", allow_network_bind=False)
    assert_bind_allowed("localhost", allow_network_bind=False)
    assert_bind_allowed("0.0.0.0", allow_network_bind=True)
    with pytest.raises(SystemExit, match="ALLOW_NETWORK_BIND"):
        assert_bind_allowed("0.0.0.0", allow_network_bind=False)
