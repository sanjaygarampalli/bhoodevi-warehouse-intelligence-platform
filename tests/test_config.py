import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_development_settings_remain_usable():
    settings = Settings(APP_ENV="development", DEBUG=True, DATABASE_URL="sqlite://")

    assert settings.DEBUG is True


@pytest.mark.parametrize(
    ("field", "value"),
    [("DEBUG", True), ("SECRET_KEY", "short")],
)
def test_deployment_settings_reject_unsafe_values(field, value):
    values = {
        "APP_ENV": "production",
        "DEBUG": False,
        "SECRET_KEY": "x" * 32,
        "DATABASE_URL": "postgresql://bwip:strong-password@db.example/bwip",
    }
    values[field] = value

    with pytest.raises(ValidationError):
        Settings(**values)


def test_deployment_settings_reject_placeholder_database_url():
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            SECRET_KEY="x" * 32,
            DATABASE_URL="postgresql://username:password@localhost:5432/bwip_db",
        )