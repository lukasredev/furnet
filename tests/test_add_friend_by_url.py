"""Tests for POST /api/friends/add, which fetches a friend's profile from their instance."""
import httpx
import pytest

from api import routes
from config import animal_config, settings

FRIEND = "dj-viscon-workshop-3.vsos.ethz.ch"


def add(client, instance_url: str) -> httpx.Response:
    return client.post("/api/friends/add", json={"instance_url": instance_url})


def test_adds_friend_from_their_profile(client, network):
    profile = network.add_instance(FRIEND, name="Buddy")

    response = add(client, f"https://{FRIEND}")

    assert response.status_code == 200
    body = response.json()
    assert body["unique_id"] == profile["id"]
    assert body["dns_name"] == FRIEND
    assert body["name"] == "Buddy"
    assert client.get("/api/friends").json() == [body]
    assert network.urls == [f"https://{FRIEND}/api/me"]


@pytest.mark.parametrize("typed", [
    FRIEND,
    f"https://{FRIEND}/",
    f"  https://{FRIEND}  ",
    f"HTTPS://{FRIEND.upper()}",
    f"https://{FRIEND}/some/page?tab=friends#top",
])
def test_normalizes_the_typed_url_to_the_instance_origin(client, network, typed):
    network.add_instance(FRIEND)

    assert add(client, typed).status_code == 200
    assert network.urls == [f"https://{FRIEND}/api/me"]


def test_keeps_an_explicit_http_scheme(client, network):
    network.add_instance(FRIEND)

    add(client, f"http://{FRIEND}")

    assert network.urls == [f"http://{FRIEND}/api/me"]


def test_strips_port_from_dns_name(client, network):
    network.add_instance(FRIEND)

    response = add(client, f"https://{FRIEND}:8443")

    assert response.status_code == 200
    assert response.json()["dns_name"] == FRIEND
    assert network.urls == [f"https://{FRIEND}:8443/api/me"]


def test_uses_a_request_timeout(client, network):
    network.add_instance(FRIEND)

    add(client, FRIEND)

    assert network.timeouts and all(t is not None and t <= 10 for t in network.timeouts)


def test_takes_the_identity_from_the_contacted_host(client, network):
    """A friend's claims about its own id and URL are not trusted."""
    network.add_instance(FRIEND, name="Buddy", id="furnet.lukasre.ch:rusty",
                         instance_url="https://furnet.lukasre.ch")

    body = add(client, FRIEND).json()

    assert body["unique_id"] == f"{FRIEND}:buddy"
    assert body["dns_name"] == FRIEND


def test_adds_an_instance_whose_instance_url_is_misconfigured(client, network):
    network.add_instance(FRIEND, name="Buddy", id="localhost:buddy", instance_url="http://localhost:8000")

    response = add(client, FRIEND)

    assert response.status_code == 200
    assert response.json()["unique_id"] == f"{FRIEND}:buddy"


def test_rejects_adding_yourself(client, network):
    our_host = settings.instance_url.removeprefix("https://")
    network.add_instance(our_host, name=animal_config.animal_name)

    response = add(client, settings.instance_url)

    assert response.status_code == 400
    assert response.json()["detail"] == "You can't add yourself as a friend!"
    assert routes.friends_db == []


def test_rejects_adding_yourself_when_your_instance_url_is_misconfigured(client, network, monkeypatch):
    monkeypatch.setattr(settings, "instance_url", "http://localhost:8000")
    network.add_instance("me.vsos.ethz.ch", name=animal_config.animal_name,
                         id=routes.generate_animal_id("http://localhost:8000", animal_config.animal_name))

    response = add(client, "me.vsos.ethz.ch")

    assert response.status_code == 400
    assert response.json()["detail"] == "You can't add yourself as a friend!"


def test_rejects_a_friend_added_twice(client, network):
    profile = network.add_instance(FRIEND)
    add(client, FRIEND)

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == f"Friend with unique_id '{profile['id']}' already exists"
    assert len(routes.friends_db) == 1


def test_rejects_when_friend_limit_reached(client, network, fill_friends):
    network.add_instance(FRIEND)
    fill_friends(1000)

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Maximum number of friends (1000) reached")
    assert len(routes.friends_db) == 1000


def test_rejects_friend_outside_allowed_domains_without_contacting_it(client, network):
    network.add_instance("furnet.example.com")

    response = add(client, "https://furnet.example.com")

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Friends must be from one of these domains: vsos.ethz.ch, furnet.lukasre.ch. "
        "Got: furnet.example.com"
    )
    assert routes.friends_db == []
    assert network.requests == []


@pytest.mark.parametrize("url, reason", [
    (f"ftp://{FRIEND}", "only http and https URLs are supported"),
    (f"https://user:secret@{FRIEND}", "URLs with credentials are not supported"),
    ("https://", "URL has no host"),
    (f"https://{FRIEND}:99999", "Port out of range 0-65535"),
    ("https://bad_host.vsos.ethz.ch", "invalid host name"),
])
def test_rejects_invalid_urls_without_contacting_anything(client, network, url, reason):
    response = add(client, url)

    assert response.status_code == 400
    assert response.json()["detail"] == f"Invalid instance URL: {reason}"
    assert network.requests == []


def test_rejects_overlong_urls(client, network):
    assert add(client, f"https://{FRIEND}/{'x' * 2048}").status_code == 422
    assert network.requests == []


@pytest.mark.parametrize("missing", ["id", "name", "instance_url"])
def test_rejects_profile_missing_required_fields(client, network, missing):
    profile = network.profile(FRIEND)
    del profile[missing]
    network.add(FRIEND, lambda request: httpx.Response(200, json=profile))

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid response from friend instance - missing required fields"
    assert routes.friends_db == []


@pytest.mark.parametrize("name", ["", "x" * 101, 42, None, ["Buddy"]])
def test_rejects_profile_with_an_invalid_name(client, network, name):
    network.add(FRIEND, lambda request: httpx.Response(200, json=network.profile(FRIEND) | {"name": name}))

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid response from friend instance - name must be 1 to 100 characters"
    assert routes.friends_db == []


@pytest.mark.parametrize("body, reason", [
    ("<html>Welcome to nginx!</html>", "not JSON"),
    ('["id", "name", "instance_url"]', "not a JSON object"),
    ("[" * 100_000, "response too large"),
    ("[" * 60_000, "not JSON"),
])
def test_rejects_a_response_that_is_not_a_profile(client, network, body, reason):
    network.add(FRIEND, lambda request: httpx.Response(200, text=body))

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == f"Invalid response from friend instance - {reason}"
    assert routes.friends_db == []


def test_reports_http_error_from_friend(client, network):
    network.add(FRIEND, lambda request: httpx.Response(503))

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        f"Failed to fetch friend's profile from https://{FRIEND}/api/me. Status: 503"
    )
    assert routes.friends_db == []


@pytest.mark.parametrize("error", [httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout])
def test_reports_unreachable_friend(client, network, error):
    def fail(request):
        raise error("connection trouble", request=request)
    network.add(FRIEND, fail)

    response = add(client, FRIEND)

    assert response.status_code == 400
    assert response.json()["detail"] == f"Failed to connect to friend instance: {error.__name__}"
    assert routes.friends_db == []


def test_reports_an_unexpected_error_without_details(client, network):
    def fail(request):
        raise RuntimeError("internal detail")
    network.add(FRIEND, fail)

    response = add(client, FRIEND)

    assert response.status_code == 500
    assert response.json()["detail"] == "Unexpected error while adding friend"


def test_requires_an_instance_url(client):
    assert client.post("/api/friends/add", json={}).status_code == 422
