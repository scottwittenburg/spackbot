import json
import pathlib
import pytest
from gidgethub import abc as gh_abc
from gidgethub import sansio
from gidgethub.abc import JSON_UTF_8_CHARSET

from spackbot.routes import router


def load_event_data(json_file):
    data_path = pathlib.Path(__file__).parent / "data" / json_file
    with data_path.open("rb") as fd:
        return fd.read()

class MockGitHubAPI(gh_abc.GitHubAPI):
    DEFAULT_HEADERS = {
        "x-ratelimit-limit": "2",
        "x-ratelimit-remaining": "1",
        "x-ratelimit-reset": "0",
        "content-type": JSON_UTF_8_CHARSET,
    }

    def __init__(
        self,
        status_code=200,
        headers=DEFAULT_HEADERS,
        body=b"",
        *,
        cache=None,
        oauth_token=None,
        base_url=sansio.DOMAIN,
    ):
        self.response_code = status_code
        self.response_headers = headers
        self.response_body = body
        super().__init__(
            "test_abc", oauth_token=oauth_token, cache=cache, base_url=base_url
        )

    async def _request(self, method, url, headers, body=b""):
        """Make an HTTP request."""
        print(f"Making a real {method} request to {url}! Wink wink!")
        self.method = method
        self.url = url
        self.headers = headers
        self.body = body
        response_headers = self.response_headers.copy()
        try:
            # Don't loop forever.
            del self.response_headers["link"]
        except KeyError:
            pass
        return self.response_code, response_headers, self.response_body

    async def sleep(self, seconds):  # pragma: no cover
        """Sleep for the specified number of seconds."""
        self.slept = seconds


@pytest.mark.asyncio
async def test_route_style_check():
    gh = MockGitHubAPI()
    headers = {
        "x-github-event": "check_run",
        "content-type": JSON_UTF_8_CHARSET,
        "x-github-delivery": "meh",
    }
    event = sansio.Event.from_http(headers, load_event_data("check_run.json"))
    await router.dispatch(event, gh, session=None)

    assert gh.method == "POST"
    assert gh.url == "https://api.github.com/repos/spack-test/spack/issues/43/comments"
    assert "It looks like you had an issue with style checks!" in gh.body.decode("utf-8")
