"""Exercise CVE-2019-25781 inputs through the Confluence rendering path."""

import signal

from mcp_atlassian.preprocessing.confluence import ConfluencePreprocessor


class RegressionTimeout(BaseException):
    """Stop conversion even when its error handler attempts a fallback."""


def fail_on_timeout(_signal_number, _frame):
    raise RegressionTimeout("Confluence Markdown rendering exceeded the regression deadline")


signal.signal(signal.SIGALRM, fail_on_timeout)
renderer = ConfluencePreprocessor("https://example.invalid/wiki")
for token in ("[", "![", "[a]("):
    payload = token * 20_000
    signal.alarm(5)
    rendered = renderer.markdown_to_confluence_storage(payload)
    signal.alarm(0)
    assert payload in rendered, token

valid = renderer.markdown_to_confluence_storage(
    '[example](https://example.invalid/a_(b) "title")'
)
assert 'href="https://example.invalid/a_(b)"' in valid, valid
assert ">example</a>" in valid, valid
