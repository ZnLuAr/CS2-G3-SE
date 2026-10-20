"""使用真实 MySQL 结构验证 CLI 进入登录菜单并退出。"""
from __future__ import annotations

from dataclasses import asdict
import json
import os

import pytest


@pytest.mark.mysql
def test_mysql_cli_reaches_login_and_exits(initialized_mysql_database, test_settings, tmp_path, run_cli):
    config = asdict(test_settings.app)
    config["log"]["directory"] = str(config["log"]["directory"])
    config["database"]["password"] = ""
    path = tmp_path / "cli-config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    env = os.environ.copy()
    env["DB_PASSWORD"] = test_settings.app.database.password
    try:
        result = run_cli(["--config", str(path)], env=env)
        assert result.returncode == 0
        assert "1 登录" in result.stdout
        assert "0 退出" in result.stdout
        assert not result.stderr
    finally:
        path.unlink(missing_ok=True)
