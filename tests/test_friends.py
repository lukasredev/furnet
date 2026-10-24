"""
Tests for listing friends, adding them from a Friend payload (POST /api/friends) and
the domain allowlist.
"""
import pytest

from api import routes
from api.routes import is_allowed_friend_domain

BUDDY = "buddy.vsos.ethz.ch"


def friend(dns_name: str = BUDDY, name: str = "Buddy", **overrides) -> dict:
    return {"unique_id": f"{dns_name}:{name.lower()}", "dns_name": dns_name, "name": name, **overrides}


def test_friend_list_starts_empty(client):
    response = client.get("/api/friends")

    assert response.status_code == 200
    assert response.json() == []


def test_add_friend_verifies_the_payload_with_the_friend_instance(client, network):
    network.add_instance(BUDDY, name="Buddy")

    response = client.post("/api/friends", json=friend())

    assert response.status_code == 200
    body = response.json()
    assert body["unique_id"] == "buddy.vsos.ethz.ch:buddy"
    assert body["dns_name"] == BUDDY
    assert body["name"] == "Buddy"
    assert body["connected_at"]
    assert client.get("/api/friends").json() == [body]
    assert network.urls == [f"https://{BUDDY}/api/me"]


def test_add_friend_stores_the_name_the_friend_serves(client, network):
    network.add_instance(BUDDY, name="buddy")

    response = client.post("/api/friends", json=friend(name="BUDDY"))

    assert response.json()["name"] == "buddy"


def test_add_friend_rejects_a_payload_that_does_not_match_the_profile(client, network):
    network.add_instance(BUDDY, name="Buddy")

    response = client.post("/api/friends", json=friend(name="Someone Else"))

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "unique_id 'buddy.vsos.ethz.ch:someone else' does not match the profile served by "
        "buddy.vsos.ethz.ch ('buddy.vsos.ethz.ch:buddy')"
    )
    assert routes.friends_db == []


def test_add_friend_rejects_an_offline_friend(client, network):
    response = client.post("/api/friends", json=friend())

    assert response.status_code == 400
    assert response.json()["detail"] == "Failed to connect to friend instance: ConnectError"
    assert routes.friends_db == []


def test_friends_are_listed_in_the_order_they_were_added(client, network):
    for name in ("Anna", "Bert", "Cleo"):
        network.add_instance(f"{name.lower()}.vsos.ethz.ch", name=name)
        client.post("/api/friends", json=friend(dns_name=f"{name.lower()}.vsos.ethz.ch", name=name))

    assert [f["name"] for f in client.get("/api/friends").json()] == ["Anna", "Bert", "Cleo"]


def test_connected_at_is_timezone_aware(client, network):
    network.add_instance(BUDDY)

    connected_at = client.post("/api/friends", json=friend()).json()["connected_at"]

    # Browsers read timestamps without an offset as local time, which shifts them
    assert connected_at.endswith(("Z", "+00:00"))


def test_add_friend_rejects_duplicate_unique_id(client, network):
    network.add_instance(BUDDY)
    client.post("/api/friends", json=friend())

    response = client.post("/api/friends", json=friend())

    assert response.status_code == 400
    assert response.json()["detail"] == "Friend with unique_id 'buddy.vsos.ethz.ch:buddy' already exists"
    assert len(routes.friends_db) == 1


def test_add_friend_rejects_domain_outside_allowlist_without_contacting_it(client, network):
    response = client.post("/api/friends", json=friend(dns_name="localhost"))

    assert response.status_code == 403
    assert response.json()["detail"].endswith("Got: localhost")
    assert routes.friends_db == []
    assert network.requests == []


def test_add_friend_enforces_limit_of_1000(client, network, fill_friends):
    network.add_instance(BUDDY)
    fill_friends(1000)

    response = client.post("/api/friends", json=friend())

    assert response.status_code == 400
    assert response.json()["detail"].startswith("Maximum number of friends (1000) reached")
    assert len(routes.friends_db) == 1000


def test_add_friend_accepts_the_1000th_friend(client, network, fill_friends):
    network.add_instance(BUDDY)
    fill_friends(999)

    assert client.post("/api/friends", json=friend()).status_code == 200
    assert len(routes.friends_db) == 1000


@pytest.mark.parametrize("missing", ["unique_id", "dns_name", "name"])
def test_add_friend_requires_all_fields(client, network, missing):
    payload = friend()
    del payload[missing]

    assert client.post("/api/friends", json=payload).status_code == 422
    assert network.requests == []


@pytest.mark.parametrize("payload", [
    friend(name=""),
    friend(name="x" * 101),
    friend(dns_name="x" * 254),
    friend(dns_name="buddy.vsos.ethz.ch:8443"),
    friend(dns_name="https://buddy.vsos.ethz.ch"),
])
def test_add_friend_validates_field_formats_and_lengths(client, network, payload):
    network.add_instance(BUDDY)

    assert client.post("/api/friends", json=payload).status_code == 422
    assert network.requests == []


@pytest.mark.parametrize("dns_name", [
    "vsos.ethz.ch",
    "furnet.lukasre.ch",
    "dj-viscon-workshop-3.vsos.ethz.ch",
    "a.b.furnet.lukasre.ch",
    "DJ-Viscon-Workshop-3.VSOS.ETHZ.CH",
    "furnet.lukasre.ch.",
])
def test_allowlist_accepts_allowed_domains_and_subdomains(dns_name):
    assert is_allowed_friend_domain(dns_name)


@pytest.mark.parametrize("dns_name", [
    "",
    "localhost",
    "example.com",
    "ethz.ch",
    "lukasre.ch",
    "evilvsos.ethz.ch",
    "vsos.ethz.ch.evil.example",
    "furnet.lukasre.ch.evil.example",
])
def test_allowlist_rejects_other_and_lookalike_domains(dns_name):
    assert not is_allowed_friend_domain(dns_name)
