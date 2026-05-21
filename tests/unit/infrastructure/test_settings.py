import pytest

from app.infrastructure.config.settings import Settings


def test_settings_database_urls():
    dummy_string = "pass"
    s = Settings(
        database_password=dummy_string,
        database_host="host",
        database_port=5432,
        database_name="db",
    )
    assert "postgresql+asyncpg://app:pass@host:5432/db" in s.database_url
    assert s.sync_database_url == "postgresql://app:pass@host:5432/db"


def test_settings_log_level_validation():
    s = Settings(log_level="DEBUG")
    assert s.log_level == "DEBUG"

    with pytest.raises(ValueError, match="log_level must be one of"):
        Settings(log_level="INVALID")


def test_settings_allowed_hosts_parsing():
    # Test JSON list parsing
    s = Settings(allowed_hosts='["a", "b"]')
    assert s.allowed_hosts == ["a", "b"]

    # Test invalid JSON brackets list parsing fallback
    s = Settings(allowed_hosts="[a, b]")
    assert s.allowed_hosts == ["a", "b"]

    # Test comma-separated parsing
    s = Settings(allowed_hosts="a, b, c")
    assert s.allowed_hosts == ["a", "b", "c"]

    # Test list input
    s = Settings(allowed_hosts=["a", "b"])
    assert s.allowed_hosts == ["a", "b"]

    # Test fallback empty list
    s = Settings(allowed_hosts=123)
    assert s.allowed_hosts == []
