from types import SimpleNamespace
import pytest
from flaxon.config import Environment, Settings


def test_typed_environment_and_precedence(tmp_path, monkeypatch):
    env = Environment()
    path = tmp_path / ".env"
    path.write_text("TEST_DEBUG=true\nTEST_HOSTS=one.example, two.example\n")
    monkeypatch.setenv("TEST_DEBUG", "false")
    env.load(path)
    assert env.bool("TEST_DEBUG") is False
    assert env.list("TEST_HOSTS") == ["one.example", "two.example"]
    monkeypatch.setenv("TEST_DEBUG", "wrong")
    with pytest.raises(ValueError):
        env.bool("TEST_DEBUG")


def test_production_settings_require_persistent_secret(tmp_path):
    source = SimpleNamespace(__file__=str(tmp_path / "settings.py"), DEBUG=False)
    with pytest.raises(ValueError, match="persistent secret"):
        Settings(source)
    source.SECRET_KEY = "a" * 48
    settings = Settings(source)
    assert settings.DATABASE_URL.startswith("sqlite:///")
    source.ALLOWED_HOSTS = ["*"]
    with pytest.raises(ValueError, match="explicit"):
        Settings(source)
