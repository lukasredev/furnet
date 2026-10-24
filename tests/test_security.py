"""
Security tests: SSRF, identity spoofing, size limits, logging and error details.

Other instances and the people typing URLs into the UI are untrusted, so these pin
down what the backend refuses to contact, store, log or reveal.
"""
import logging

import httpx
import pytest

from api import routes

ALLOWED = "dj-viscon-workshop-3.vsos.ethz.ch"
METADATA_URL = "http://169.254.169.254/latest/meta-data/"


def health_check(client, *instance_urls: str) -> list[dict]:
    return client.post("/api/health-check", json={"instance_urls": list(instance_urls)}).json()


# --- Server-side request forgery ---------------------------------------------

def test_add_friend_does_not_contact_hosts_outside_allowlist(client, network):
    # The trailing "?" would turn an appended "/api/me" into a query string
    response = client.post("/api/friends/add", json={"instance_url": f"{METADATA_URL}iam?"})

    assert response.status_code == 403
    assert network.requests == []


@pytest.mark.parametrize("url", [
    f"{METADATA_URL}iam?",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://[::1]:8000",
    "http://[::ffff:127.0.0.1]",
    "http://0.0.0.0:8000",
    "http://10.0.0.1",
    "http://192.168.1.1",
    "http://100.64.0.1",
])
def test_health_check_does_not_contact_internal_addresses(client, network, url):
    [result] = health_check(client, url)

    assert result["is_alive"] is False
    assert result["error"] == "Blocked: not a public address"
    assert network.requests == []


def test_health_check_blocks_names_that_resolve_to_internal_addresses(client, network):
    network.dns["internal.example"] = ["10.1.2.3"]
    network.dns["2130706433"] = ["127.0.0.1"]  # How resolvers read a decimal IPv4 address

    results = health_check(client, "internal.example", "http://2130706433:8000")

    assert [r["error"] for r in results] == ["Blocked: not a public address"] * 2
    assert network.requests == []


def test_health_check_blocks_a_name_with_any_internal_address(client, network):
    network.add_instance("mixed.example")
    network.dns["mixed.example"] = [network.public_ip, "10.1.2.3"]

    [result] = health_check(client, "mixed.example")

    assert result["error"] == "Blocked: not a public address"
    assert network.requests == []


def test_health_check_connects_to_the_address_it_checked(client, network, monkeypatch):
    """A DNS answer that changes after the check (DNS rebinding) cannot redirect the request."""
    network.add_instance("rebind.example")
    answers = iter([[network.public_ip], ["127.0.0.1"]])

    async def rebinding_lookup(host, port):
        return next(answers)
    monkeypatch.setattr(routes, "lookup_addresses", rebinding_lookup)

    [result] = health_check(client, "rebind.example")

    assert result["is_alive"] is True
    assert network.connected_to == [network.public_ip]


def test_add_friend_does_not_follow_redirects(client, network):
    network.add(ALLOWED, lambda request: httpx.Response(302, headers={"location": METADATA_URL}))

    response = client.post("/api/friends/add", json={"instance_url": ALLOWED})

    assert response.status_code == 400
    assert routes.friends_db == []
    assert network.urls == [f"https://{ALLOWED}/api/me"]


def test_health_check_does_not_follow_redirects(client, network):
    network.add(ALLOWED, lambda request: httpx.Response(302, headers={"location": METADATA_URL}))

    [result] = health_check(client, ALLOWED)

    assert result["error"] == "HTTP 302"
    assert network.urls == [f"https://{ALLOWED}/api/me"]


# --- Identity ------------------------------------------------------------------

def test_server_outside_allowlist_cannot_pose_as_a_workshop_instance(client, network):
    network.add_instance("evil.example", name="Rusty", instance_url=f"https://{ALLOWED}",
                         id=f"{ALLOWED}:rusty")

    response = client.post("/api/friends/add", json={"instance_url": "https://evil.example"})

    assert response.status_code == 403
    assert routes.friends_db == []
    assert network.requests == []


def test_workshop_instance_cannot_pose_as_another_one(client, network):
    network.add_instance(ALLOWED, name="Rusty", instance_url="https://dj-viscon-workshop-7.vsos.ethz.ch",
                         id="dj-viscon-workshop-7.vsos.ethz.ch:rusty")

    friend = client.post("/api/friends/add", json={"instance_url": ALLOWED}).json()

    assert friend["unique_id"] == f"{ALLOWED}:rusty"
    assert friend["dns_name"] == ALLOWED


@pytest.mark.parametrize("dns_name", [
    "evil.example/.vsos.ethz.ch",
    "evil.example?.vsos.ethz.ch",
    "evil.example#.furnet.lukasre.ch",
    "evil.example@x.vsos.ethz.ch",
])
def test_add_friend_rejects_dns_name_that_is_not_a_hostname(client, network, dns_name):
    response = client.post("/api/friends", json={"unique_id": "x:y", "dns_name": dns_name, "name": "y"})

    assert response.status_code == 422
    assert routes.friends_db == []
    assert network.requests == []


def test_friend_names_are_returned_as_plain_data(client, network):
    """Script in a remote profile is stored and returned verbatim; the UI renders it as text."""
    payload = "<img src=x onerror=alert(1)>"
    network.add_instance(ALLOWED, name=payload)

    response = client.post("/api/friends/add", json={"instance_url": ALLOWED})

    assert response.headers["content-type"] == "application/json"
    assert response.json()["name"] == payload


# --- Size limits ---------------------------------------------------------------

def test_add_friend_rejects_an_oversized_profile(client, network):
    network.add_instance(ALLOWED, name="x" * 1_000_000)

    response = client.post("/api/friends/add", json={"instance_url": ALLOWED})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid response from friend instance - response too large"
    assert routes.friends_db == []


def test_oversized_responses_are_not_read_to_the_end(client, network):
    chunks_sent = 0

    async def endless_body():
        nonlocal chunks_sent
        while chunks_sent < 10_000:
            chunks_sent += 1
            yield b"x" * 1024
    network.add(ALLOWED, lambda request: httpx.Response(200, content=endless_body()))

    [result] = health_check(client, ALLOWED)

    assert result["error"] == "Invalid response: response too large"
    assert chunks_sent < 100


# --- Cross-site requests -------------------------------------------------------

@pytest.mark.parametrize("path, body", [
    ("/api/friends", f'{{"unique_id": "{ALLOWED}:buddy", "dns_name": "{ALLOWED}", "name": "Buddy"}}'),
    ("/api/friends/add", f'{{"instance_url": "{ALLOWED}"}}'),
    ("/api/health-check", f'{{"instance_urls": ["{ALLOWED}"]}}'),
])
@pytest.mark.parametrize("content_type", ["text/plain", "application/x-www-form-urlencoded"])
def test_endpoints_reject_bodies_a_cross_site_form_can_send(client, network, path, body, content_type):
    """Other websites can make a visitor's browser send these without a CORS preflight."""
    network.add_instance(ALLOWED)

    response = client.post(path, content=body, headers={"content-type": content_type})

    assert response.status_code == 422
    assert routes.friends_db == []
    assert network.requests == []


def test_cors_allows_the_vite_dev_origin_only(client):
    def preflight(origin):
        return client.options(
            "/api/friends",
            headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
        )

    assert preflight("http://localhost:5173").headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in preflight("https://evil.example").headers


# --- Logs and error details ----------------------------------------------------

@pytest.fixture
def logs(caplog):
    caplog.set_level(logging.DEBUG, logger="api.routes")
    return caplog


def test_untrusted_text_cannot_forge_log_lines(client, network, logs):
    network.add_instance(ALLOWED, name="Buddy\n2026-10-24 CRITICAL forged entry")

    health_check(client, ALLOWED, "evil.example\n2026-10-24 CRITICAL forged entry")

    messages = [record.getMessage() for record in logs.records]
    assert messages
    assert not any("\n" in message for message in messages)


def test_remote_responses_are_not_logged(client, network, logs):
    network.add_instance(ALLOWED, fun_fact="secret-token-123")

    health_check(client, ALLOWED)

    assert not any("secret-token-123" in record.getMessage() for record in logs.records)


def test_connection_errors_are_not_revealed_to_the_client(client, network, logs):
    def fail(request):
        raise httpx.ConnectError("connect to 10.20.30.40:443 refused", request=request)
    network.add(ALLOWED, fail)

    response = client.post("/api/friends/add", json={"instance_url": ALLOWED})

    assert response.json()["detail"] == "Failed to connect to friend instance: ConnectError"
    assert any("10.20.30.40" in record.getMessage() for record in logs.records)
