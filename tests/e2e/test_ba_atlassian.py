"""End to end (R4): the admin adds an OAuth MCP server and signs in from the MCP page; BA Studio connects with the member's
own sign-in, searches and attaches. The provider is the local OAuth + MCP stand-in (tests/fixtures/mcp_oauth_server.py);
the real Atlassian server needs an Atlassian account. No model is used."""
import re

import pytest
from playwright.sync_api import expect

from tests.e2e.helpers_app import UI, shot
from tests.test_atlassian_r4 import base  # noqa: F401 - the provider fixture

pytestmark = pytest.mark.e2e


def test_connect_search_and_attach_jira_and_confluence_from_ba_studio(page, base):  # noqa: F811
    server = page.request.post(f"{UI}/api/mcp/servers", data={"name": "Atlassian", "transport": "http", "url": f"{base}/mcp", "auth": "oauth"}).json()
    page.goto(f"{UI}/mcp")
    card = page.get_by_test_id("mcp-server-card").filter(has_text="Atlassian")
    card.get_by_role("button", name="Sign in").click()  # to the provider and back, through the browser
    expect(page).to_have_url(re.compile(r"/mcp\?connected="), timeout=30_000)
    page.get_by_test_id("mcp-server-card").filter(has_text="Atlassian").get_by_test_id("mcp-connect").click()
    expect(page.get_by_test_id("mcp-server-card").filter(has_text="Atlassian").get_by_test_id("mcp-tool-row")).to_have_count(2, timeout=30_000)
    assert page.request.post(f"{UI}/api/mcp/grants", data={"server_id": server["id"], "tool_name": "*", "role": "admin"}).status in (201, 400)

    project = page.request.post(f"{UI}/api/projects", data={"name": "Outside sources", "description": ""}).json()
    page.goto(f"{UI}/projects/{project['id']}/ba")
    outside = page.get_by_test_id("outside-source")
    expect(outside).to_be_visible(timeout=30_000)
    outside.get_by_label("Search Atlassian").fill("refund")
    outside.get_by_role("button").nth(0).click()
    outside.get_by_text("PAY-142 Refund rules").click()
    outside.get_by_role("button", name="Attach selected").click()
    expect(page.get_by_text("PAY-142 Refund rules.md")).to_be_visible(timeout=30_000)
    shot(page, "r4-ba-studio-attached")
