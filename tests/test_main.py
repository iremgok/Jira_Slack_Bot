import pytest

from src.core.config import get_settings
from src.core.exceptions import RepositoryError
from src.database.db import wait_for_database
from src.main import main


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    for key, value in {
        "JIRA_BASE_URL": "https://example.atlassian.net",
        "JIRA_PROJECT_KEY": "KAN",
        "JIRA_MOCK_MODE": "true",
        "SLACK_DRY_RUN": "true",
        "DATABASE_URL": f"sqlite:///{(tmp_path / 'bot.db').as_posix()}",
        "LOG_DIR": "",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)  # make sure no developer .env is picked up
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_once_poll_and_report_end_to_end(mock_env):
    assert main(["--once", "poll"]) == 0
    assert main(["--once", "report"]) == 0
    assert main(["--check"]) == 0


def test_invalid_config_exit_code(mock_env, monkeypatch):
    monkeypatch.setenv("JIRA_MOCK_MODE", "false")
    get_settings.cache_clear()
    assert main(["--once", "poll"]) == 2


def test_wait_for_database_times_out(tmp_path):
    url = f"sqlite:///{(tmp_path / 'missing-dir' / 'x.db').as_posix()}"
    with pytest.raises(RepositoryError, match="not reachable"):
        wait_for_database(url, timeout_seconds=0)
