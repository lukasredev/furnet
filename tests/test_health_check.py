"""Tests for POST /api/health-check, which the Monitoring page polls."""
import asyncio

import httpx
import pytest

FRIEND = "dj-viscon-workshop-3.vsos.ethz.ch"
OUTSIDER = "furnet.example.com"


def check(client, *instance_urls: str) -> list[dict]:
    response = client.post("/api/health-check", json={"instance_urls": list(instance_urls)})
    assert response.status_code == 200
    return response.json()


def test_reports_online_instance_with_its_name_and_emoji(client, network):
    network.add_instance(FRIEND, name="Buddy", emoji="🦊")

    [result] = check(client, f"https://{FRIEND}")

    assert result["instance_url"] == f"https://{FRIEND}"
    assert result["is_alive"] is True
    assert result["error"] is None
    assert result["name"] == "Buddy"
    assert result["emoji"] == "🦊"
    assert result["response_time_ms"] >= 0
    assert network.urls == [f"https://{FRIEND}/api/me"]
    assert network.connected_to == [FRIEND]


def test_checks_hosts_outside_the_allowlist_on_the_public_address_it_verified(client, network):
    network.add_instance(OUTSIDER, name="Ozzy")

    [result] = check(client, f"https://{OUTSIDER}")

    assert result["is_alive"] is True
    assert result["name"] == "Ozzy"
    [request] = network.requests
    assert request.url.host == network.public_ip
    assert request.headers["host"] == OUTSIDER
    assert request.extensions["sni_hostname"] == OUTSIDER
    assert network.urls == [f"https://{OUTSIDER}/api/me"]


def test_keeps_a_non_default_port_when_pinning_the_address(client, network):
    network.add_instance(OUTSIDER)

    check(client, f"http://{OUTSIDER}:8080")

    assert network.urls == [f"http://{OUTSIDER}:8080/api/me"]
    assert network.connected_to == [network.public_ip]


def test_reports_unresolvable_host_as_offline(client, network):
    [result] = check(client, "https://nowhere.example")

    assert result["is_alive"] is False
    assert result["error"] == "Connection failed: ConnectError"
    assert network.requests == []


def test_any_json_object_counts_as_online(client, network):
    network.add(FRIEND, lambda request: httpx.Response(200, json={}))

    [result] = check(client, f"https://{FRIEND}")

    assert result["is_alive"] is True
    assert result["name"] is None
    assert result["emoji"] is None


@pytest.mark.parametrize("name, emoji", [("x" * 101, "🦊" * 33), (42, ["🦊"])])
def test_ignores_names_and_emoji_that_are_too_long_or_not_text(client, network, name, emoji):
    network.add(FRIEND, lambda request: httpx.Response(200, json={"name": name, "emoji": emoji}))

    [result] = check(client, f"https://{FRIEND}")

    assert result["is_alive"] is True
    assert result["name"] is None
    assert result["emoji"] is None


def test_reports_http_error_as_offline(client, network):
    network.add(FRIEND, lambda request: httpx.Response(502))

    [result] = check(client, f"https://{FRIEND}")

    assert result["is_alive"] is False
    assert result["error"] == "HTTP 502"
    assert result["name"] is None
    assert result["response_time_ms"] >= 0


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout])
def test_reports_unreachable_instance_as_offline(client, network, error):
    def fail(request):
        raise error("connection trouble", request=request)
    network.add(FRIEND, fail)

    [result] = check(client, f"https://{FRIEND}")

    assert result["is_alive"] is False
    assert result["error"] == f"Connection failed: {error.__name__}"


@pytest.mark.parametrize("body, reason", [
    ("<html>Welcome to nginx!</html>", "not JSON"),
    ('["not", "a", "profile"]', "not a JSON object"),
    ('{"name": "' + "x" * 70_000 + '"}', "response too large"),
])
def test_reports_a_response_that_is_not_a_profile_as_offline(client, network, body, reason):
    network.add(FRIEND, lambda request: httpx.Response(200, text=body))

    [result] = check(client, f"https://{FRIEND}")

    assert result["is_alive"] is False
    assert result["error"] == f"Invalid response: {reason}"


@pytest.mark.parametrize("typed", [
    FRIEND,
    f"https://{FRIEND}/",
    f"  https://{FRIEND}  ",
    f"https://{FRIEND}/monitoring?x=1#top",
])
def test_normalizes_urls_to_the_instance_origin(client, network, typed):
    network.add_instance(FRIEND)

    [result] = check(client, typed)

    assert result["instance_url"] == f"https://{FRIEND}"
    assert network.urls == [f"https://{FRIEND}/api/me"]


def test_reports_invalid_urls_without_contacting_anything(client, network):
    [result] = check(client, f"ftp://{FRIEND}")

    assert result == {
        "instance_url": f"ftp://{FRIEND}",
        "is_alive": False,
        "response_time_ms": None,
        "error": "Invalid URL: only http and https URLs are supported",
        "name": None,
        "emoji": None,
    }
    assert network.requests == []


def test_checks_every_instance_and_keeps_their_order(client, network):
    network.add_instance("a.vsos.ethz.ch", name="Anna")
    network.add("b.vsos.ethz.ch", lambda request: httpx.Response(500))
    network.add_instance("c.vsos.ethz.ch", name="Cleo")

    results = check(client, "a.vsos.ethz.ch", "b.vsos.ethz.ch", "offline.vsos.ethz.ch", "not a url", "c.vsos.ethz.ch")

    assert [(r["instance_url"], r["is_alive"], r["name"]) for r in results] == [
        ("https://a.vsos.ethz.ch", True, "Anna"),
        ("https://b.vsos.ethz.ch", False, None),
        ("https://offline.vsos.ethz.ch", False, None),
        ("not a url", False, None),
        ("https://c.vsos.ethz.ch", True, "Cleo"),
    ]


def test_checks_instances_concurrently(client, network):
    in_flight, peak = 0, 0

    async def slow_profile(request):
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.01)
        in_flight -= 1
        return httpx.Response(200, json={})

    hosts = [f"i{n}.vsos.ethz.ch" for n in range(5)]
    for host in hosts:
        network.add(host, slow_profile)

    assert all(r["is_alive"] for r in check(client, *hosts))
    assert peak == 5


def test_uses_a_request_timeout(client, network):
    check(client, f"https://{FRIEND}")

    assert network.timeouts and all(t is not None and t <= 10 for t in network.timeouts)


def test_empty_list_returns_no_results(client, network):
    assert check(client) == []
    assert network.requests == []


def test_accepts_up_to_50_urls(client, network):
    assert len(check(client, *[f"i{n}.vsos.ethz.ch" for n in range(50)])) == 50


def test_rejects_more_than_50_urls(client, network):
    response = client.post("/api/health-check", json={"instance_urls": [f"i{n}.vsos.ethz.ch" for n in range(51)]})

    assert response.status_code == 422
    assert network.requests == []


def test_rejects_overlong_urls(client, network):
    response = client.post("/api/health-check", json={"instance_urls": [f"https://{FRIEND}/{'x' * 2048}"]})

    assert response.status_code == 422


def test_requires_a_list_of_urls(client):
    assert client.post("/api/health-check", json={"instance_urls": "a.vsos.ethz.ch"}).status_code == 422
