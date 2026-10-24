"""
Shared fixtures for the FurNet backend tests.

The backend keeps its state in module-level lists and talks to other instances over
httpx, so these fixtures reset that state for every test and replace both DNS and the
network with an in-process fake. No test ever reaches a real host.
"""
import ipaddress
import socket

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from api import routes
from api.models import Friend
from api.routes import generate_animal_id
from config import settings

# The URL this instance pretends to be hosted at during tests
OUR_URL = "https://dj-viscon-workshop-0.vsos.ethz.ch"

class FakeNetwork:
    """
    Stands in for DNS and the internet: routes requests to per-host handlers and records them.

    Requests are routed by their Host header, so they reach the right handler even when
    the backend connects to a pinned IP address. Requests to a host without a handler
    fail with ConnectError, like an offline peer.
    """

    # A public address the fake DNS hands out for served hosts; nothing is ever sent to it
    public_ip = "93.184.216.34"

    def __init__(self):
        self.handlers = {}
        self.dns = {"localhost": ["127.0.0.1", "::1"]}
        self.requests: list[httpx.Request] = []
        self.timeouts = []

    @property
    def urls(self) -> list[str]:
        """The requested URLs, with the host each request was meant for."""
        return [
            str(request.url.copy_with(netloc=request.headers["host"].encode("ascii")))
            for request in self.requests
        ]

    @property
    def connected_to(self) -> list[str]:
        """The host or IP address each request was actually sent to."""
        return [request.url.host for request in self.requests]

    @staticmethod
    def profile(host: str, name: str = "Buddy", **overrides) -> dict:
        """The /api/me payload a FurNet instance at `host` would serve."""
        data = {
            "id": generate_animal_id(f"https://{host}", name),
            "name": name,
            "species": "Arctic Fox",
            "description": "A friendly fox",
            "instance_url": f"https://{host}",
            "emoji": "🦊",
        }
        data.update(overrides)
        return data

    def add(self, host: str, handler) -> None:
        """Serve `host` with `handler`: request -> httpx.Response (or raise an httpx error)."""
        self.handlers[host] = handler

    def add_instance(self, host: str, **profile_overrides) -> dict:
        """Serve a FurNet profile at https://<host>/api/me and return it."""
        profile = self.profile(host, **profile_overrides)

        def handler(request):
            if request.url.path == "/api/me":
                return httpx.Response(200, json=profile)
            return httpx.Response(404)

        self.add(host, handler)
        return profile

    async def lookup(self, host: str, port: int) -> list[str]:
        """Fake DNS: IP literals resolve to themselves, served hosts to public_ip."""
        if host in self.dns:
            return self.dns[host]
        try:
            return [str(ipaddress.ip_address(host))]
        except ValueError:
            pass
        if host in self.handlers:
            return [self.public_ip]
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    def __call__(self, request: httpx.Request):
        self.requests.append(request)
        host = httpx.URL(f"http://{request.headers['host']}").host
        handler = self.handlers.get(host)
        if handler is None:
            raise httpx.ConnectError("Name or service not known", request=request)
        return handler(request)


@pytest.fixture(autouse=True)
def network(monkeypatch) -> FakeNetwork:
    """Route DNS lookups and every httpx.AsyncClient the backend creates through a FakeNetwork."""
    fake = FakeNetwork()
    real_async_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        fake.timeouts.append(kwargs.get("timeout"))
        return real_async_client(*args, transport=httpx.MockTransport(fake), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    monkeypatch.setattr(routes, "lookup_addresses", fake.lookup)
    return fake


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch):
    """Give every test a known instance URL and no friends."""
    monkeypatch.setattr(settings, "instance_url", OUR_URL)
    routes.friends_db.clear()
    yield
    routes.friends_db.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(main.app)


@pytest.fixture
def fill_friends():
    """Fill the friend list with `count` placeholder friends."""
    def fill(count: int = 1000) -> None:
        routes.friends_db.extend(
            Friend(
                unique_id=f"friend-{n}.vsos.ethz.ch:pal",
                dns_name=f"friend-{n}.vsos.ethz.ch",
                name="Pal",
            )
            for n in range(count)
        )
    return fill
