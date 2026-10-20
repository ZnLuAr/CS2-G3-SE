"""配置解析与外部字段校验。"""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

import pytest

from src.config import load_config
from src.errors.business import InvalidInputError


def _config(path: Path, *, password: str = "file-pass") -> Path:
    path.write_text(json.dumps({
        "database": {"host": "localhost", "port": 3306, "database": "gym", "username": "u", "password": password},
        "timezone_name": "Asia/Shanghai",
    }), encoding="utf-8")
    return path



def _temporary_config() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=Path.cwd(), encoding="utf-8", delete=False
    ) as file:
        path = Path(file.name)
    return _config(path)



def test_load_config_environment_empty_password_overrides_file(monkeypatch):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", dir=Path.cwd(), encoding="utf-8", delete=False
    ) as file:
        path = Path(file.name)
    try:
        _config(path)
        monkeypatch.setenv("DB_PASSWORD", "")
        settings = load_config(str(path))
        assert settings.database.password == ""
        assert settings.log.directory == (Path.cwd() / "logs").resolve()
    finally:
        path.unlink(missing_ok=True)



def test_load_config_parses_optional_web_settings():
    path = _temporary_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["web"] = {
            "host": "127.0.0.1",
            "port": 8123,
            "allowed_origins": ["http://localhost:5173"],
            "issuer": "gym-test",
            "audience": "gym-browser",
            "token_lifetime_seconds": 3600,
            "jwt_secret_env_var": "TEST_JWT_SECRET",
        }
        path.write_text(json.dumps(data), encoding="utf-8")

        settings = load_config(str(path))

        assert settings.web.port == 8123
        assert settings.web.allowed_origins == ("http://localhost:5173",)
        assert settings.web.issuer == "gym-test"
        assert settings.web.token_lifetime_seconds == 3600
        assert settings.web.jwt_secret_env_var == "TEST_JWT_SECRET"
    finally:
        path.unlink(missing_ok=True)



@pytest.mark.parametrize(
    "web",
    [
        {"port": True},
        {"allowed_origins": "http://localhost:5173"},
        {"jwt_secret_env_var": "TEST;SECRET"},
        {"token_lifetime_seconds": 0},
    ],
)
def test_load_config_rejects_invalid_web_settings(web):
    path = _temporary_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["web"] = web
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(InvalidInputError):
            load_config(str(path))
    finally:
        path.unlink(missing_ok=True)
