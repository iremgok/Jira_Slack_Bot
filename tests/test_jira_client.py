import pytest

from src.core.exceptions import JiraAuthError, JiraError
from src.services.jira_client import JiraClient, build_jql
from tests.conftest import BASE_URL, raw_issue


class FakeResponse:
    def __init__(self, status: int, body: dict) -> None:
        self.status_code = status
        self._body = body
        self.ok = 200 <= status < 300
        self.text = str(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, dict(params or {})))
        return self.responses.pop(0)

    def close(self):
        pass


def make_client(responses):
    client = JiraClient(BASE_URL, "me@example.com", "token")
    client.session = FakeSession(responses)
    return client


def test_build_jql():
    jql = build_jql("KAN", "updated >= -5m", extra="sprint in openSprints()", order_by="updated ASC")
    assert jql == 'project = "KAN" AND (updated >= -5m) AND (sprint in openSprints()) ORDER BY updated ASC'


def test_search_follows_next_page_token():
    client = make_client([
        FakeResponse(200, {"issues": [raw_issue("KAN-1")], "nextPageToken": "abc", "isLast": False}),
        FakeResponse(200, {"issues": [raw_issue("KAN-2")], "isLast": True}),
    ])
    issues = client.search_issues("project = KAN")
    assert [i.key for i in issues] == ["KAN-1", "KAN-2"]
    assert client.session.calls[0][0].endswith("/rest/api/3/search/jql")
    assert client.session.calls[1][1]["nextPageToken"] == "abc"


def test_search_skips_malformed_issue():
    client = make_client([FakeResponse(200, {"issues": [{"fields": {}}, raw_issue("KAN-9")], "isLast": True})])
    assert [i.key for i in client.search_issues("x")] == ["KAN-9"]


def test_auth_error():
    client = make_client([FakeResponse(401, {})])
    with pytest.raises(JiraAuthError):
        client.search_issues("x")


def test_bad_jql_reports_jira_message():
    client = make_client([FakeResponse(400, {"errorMessages": ["Field 'foo' does not exist"]})])
    with pytest.raises(JiraError, match="foo"):
        client.search_issues("foo = bar")
