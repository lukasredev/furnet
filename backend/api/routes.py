from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Annotated, List
from urllib.parse import urlparse, urlsplit
import asyncio
import ipaddress
import json
import re
import socket
import httpx
import time
import logging
from api.models import Animal, Friend, HOSTNAME_PATTERN, MAX_HOSTNAME_LENGTH, MAX_NAME_LENGTH
from config import settings, animal_config

logger = logging.getLogger(__name__)

router = APIRouter()

# Limits for talking to other instances, which may be slow, broken or hostile
MAX_FRIENDS = 1000
MAX_HEALTH_CHECK_URLS = 50
MAX_URL_LENGTH = 2048
MAX_PROFILE_BYTES = 64 * 1024
MAX_EMOJI_LENGTH = 32


def generate_animal_id(instance_url: str, animal_name: str) -> str:
    """
    Generate a unique identifier for this FurNet instance.

    Format: domain:animal_name (e.g., "furnet-workshop.example.com:rusty")
    """
    parsed = urlparse(instance_url)
    domain = parsed.netloc if parsed.netloc else parsed.path
    # Remove port if present for cleaner ID
    domain_without_port = domain.split(':')[0] if ':' in domain else domain
    # Normalize animal name to lowercase and replace spaces with hyphens
    normalized_name = animal_name.lower().replace(' ', '-')
    return f"{domain_without_port}:{normalized_name}"


# Domains that friends are allowed to come from (the domain itself or any subdomain)
ALLOWED_FRIEND_DOMAINS = ("vsos.ethz.ch", "furnet.lukasre.ch")


def is_allowed_friend_domain(dns_name: str) -> bool:
    """Check whether a friend's DNS name is one of the allowed domains or a subdomain of one."""
    dns_name = dns_name.lower().rstrip('.')
    return any(
        dns_name == domain or dns_name.endswith(f".{domain}")
        for domain in ALLOWED_FRIEND_DOMAINS
    )


class InvalidProfileError(Exception):
    """A remote instance answered, but not with a usable FurNet profile."""


class BlockedAddressError(Exception):
    """A host resolves to an address the backend must not contact (loopback, private, ...)."""


def instance_origin(instance_url: str) -> str:
    """
    Reduce a user-supplied instance URL to its origin: scheme, host and optional port.

    Adds https:// when no scheme is given. Any path, query or fragment is dropped so it
    cannot change where the /api/me request goes. Raises ValueError for anything other
    than a plain http(s) URL of a host.
    """
    url = instance_url.strip()
    if '://' not in url:
        url = 'https://' + url
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https'):
        raise ValueError("only http and https URLs are supported")
    if parts.username is not None or parts.password is not None:
        raise ValueError("URLs with credentials are not supported")
    host = (parts.hostname or '').rstrip('.')
    if not host:
        raise ValueError("URL has no host")
    if ':' in host:
        ipaddress.IPv6Address(host)  # Raises ValueError if it is not one
        host = f"[{host}]"
    elif len(host) > MAX_HOSTNAME_LENGTH or not re.fullmatch(HOSTNAME_PATTERN, host):
        raise ValueError("invalid host name")
    port = parts.port  # Raises ValueError for an invalid port
    return f"{parts.scheme}://{host}" + (f":{port}" if port else "")


async def lookup_addresses(host: str, port: int) -> List[str]:
    """Resolve a host to its IP addresses (a separate function so tests can fake DNS)."""
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


async def resolve_public_address(host: str, port: int) -> str:
    """
    Resolve a host and return one of its addresses to connect to.

    Raises BlockedAddressError if any of its addresses is not public (loopback, private,
    link-local such as cloud metadata endpoints, ...), and httpx.ConnectError if the
    host does not resolve.
    """
    try:
        addresses = await lookup_addresses(host, port)
    except socket.gaierror as e:
        raise httpx.ConnectError(f"Could not resolve {host}") from e
    if not addresses or not all(ipaddress.ip_address(address).is_global for address in addresses):
        raise BlockedAddressError(host)
    return addresses[0]


async def fetch_profile(client: httpx.AsyncClient, origin: str, address: str | None = None) -> dict:
    """
    Fetch <origin>/api/me and return the profile.

    With `address`, the request connects to that IP instead of resolving the host again,
    so a DNS answer that changes after the address was checked cannot send it elsewhere.
    Raises httpx errors for connection and HTTP failures, and InvalidProfileError for a
    response that is too large or not a JSON object.
    """
    url = httpx.URL(origin).join("/api/me")
    headers, extensions = {}, {}
    if address:
        headers["Host"] = url.netloc.decode("ascii")
        extensions["sni_hostname"] = url.host
        url = url.copy_with(host=address)

    async with client.stream("GET", url, headers=headers, extensions=extensions) as response:
        response.raise_for_status()
        body = bytearray()
        async for chunk in response.aiter_bytes():
            body += chunk
            if len(body) > MAX_PROFILE_BYTES:
                raise InvalidProfileError("response too large")

    try:
        profile = json.loads(body)
    except (ValueError, RecursionError):
        raise InvalidProfileError("not JSON") from None
    if not isinstance(profile, dict):
        raise InvalidProfileError("not a JSON object")
    return profile


def short_text(value: object, max_length: int) -> str | None:
    """Return `value` if it is a string of at most `max_length` characters, else None."""
    return value if isinstance(value, str) and len(value) <= max_length else None


# Request model for adding friends by URL
class AddFriendRequest(BaseModel):
    instance_url: str = Field(..., max_length=MAX_URL_LENGTH)

# Request model for health check
class HealthCheckRequest(BaseModel):
    instance_urls: List[Annotated[str, Field(max_length=MAX_URL_LENGTH)]] = Field(
        ..., max_length=MAX_HEALTH_CHECK_URLS)

# Response model for health check
class InstanceHealth(BaseModel):
    instance_url: str
    is_alive: bool
    response_time_ms: float | None = None
    error: str | None = None
    name: str | None = None
    emoji: str | None = None

# In-memory storage for friend connections
friends_db: List[Friend] = []

# Animal identity endpoint
@router.get("/me", response_model=Animal)
async def get_me():
    """
    Get the animal identity of this FurNet instance.

    Returns the configured animal information including name, species,
    description, and optional fields like habitat, diet, and fun facts.
    """
    # Generate unique identifier from instance URL + animal name
    unique_id = generate_animal_id(settings.instance_url, animal_config.animal_name)

    animal = Animal(
        id=unique_id,
        name=animal_config.animal_name,
        species=animal_config.animal_species,
        description=animal_config.animal_description,
        instance_url=settings.instance_url,
        habitat=animal_config.animal_habitat,
        diet=animal_config.animal_diet,
        fun_fact=animal_config.animal_fun_fact,
        emoji=animal_config.animal_emoji,
        color=animal_config.animal_color,
    )
    return animal


async def add_verified_friend(instance_url: str, expected_unique_id: str | None = None) -> Friend:
    """
    Fetch a friend's profile from their instance, verify it and add the friend.

    Only allowlisted hosts are contacted, and the friend's identity (dns_name and
    unique_id) comes from the host that was contacted, never from what the remote
    reports about itself, so no server can pose as another instance.
    """
    try:
        origin = instance_origin(instance_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid instance URL: {e}")

    # Validate that the friend is from one of the allowed domains before contacting it
    dns_name = urlsplit(origin).hostname
    if not is_allowed_friend_domain(dns_name):
        raise HTTPException(
            status_code=403,
            detail=f"Friends must be from one of these domains: {', '.join(ALLOWED_FRIEND_DOMAINS)}. Got: {dns_name}"
        )

    friend_me_url = f"{origin}/api/me"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            friend_data = await fetch_profile(client, origin)
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch friend's profile from {friend_me_url}. Status: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.warning("Could not connect to friend instance %r: %r", origin, e)
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to friend instance: {type(e).__name__}"
        )
    except InvalidProfileError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response from friend instance - {e}"
        )
    except Exception:
        logger.exception("Unexpected error while fetching friend profile from %r", origin)
        raise HTTPException(status_code=500, detail="Unexpected error while adding friend")

    # Validate that we got the expected fields
    if not all(key in friend_data for key in ['id', 'name', 'instance_url']):
        raise HTTPException(
            status_code=400,
            detail="Invalid response from friend instance - missing required fields"
        )

    name = friend_data['name']
    if not isinstance(name, str) or not 1 <= len(name) <= MAX_NAME_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid response from friend instance - name must be 1 to {MAX_NAME_LENGTH} characters"
        )
    new_friend = Friend(unique_id=generate_animal_id(origin, name), dns_name=dns_name, name=name)

    # Check if trying to add yourself, also by the ID a misconfigured instance reports
    our_id = generate_animal_id(settings.instance_url, animal_config.animal_name)
    if our_id in (new_friend.unique_id, friend_data['id']):
        raise HTTPException(
            status_code=400,
            detail="You can't add yourself as a friend!"
        )

    if expected_unique_id is not None and new_friend.unique_id != expected_unique_id:
        raise HTTPException(
            status_code=400,
            detail=f"unique_id '{expected_unique_id}' does not match the profile served by {dns_name} ('{new_friend.unique_id}')"
        )

    # Check if friend already exists
    for existing_friend in friends_db:
        if existing_friend.unique_id == new_friend.unique_id:
            raise HTTPException(
                status_code=400,
                detail=f"Friend with unique_id '{new_friend.unique_id}' already exists"
            )

    # Check if we've reached the maximum number of friends
    if len(friends_db) >= MAX_FRIENDS:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum number of friends ({MAX_FRIENDS}) reached. Cannot add more friends."
        )

    friends_db.append(new_friend)
    return new_friend


# Friend connection endpoints
@router.post("/friends", response_model=Friend)
async def add_friend(friend: Friend):
    """
    Add a friend connection from a Friend payload.

    The payload is only a claim: the friend's profile is fetched from https://<dns_name>,
    its unique_id must match the payload, and the friend is stored as that instance
    describes itself.
    """
    return await add_verified_friend(friend.dns_name, expected_unique_id=friend.unique_id)


@router.get("/friends", response_model=List[Friend])
async def get_friends():
    """
    Get all friend connections for this FurNet instance.

    Returns a list of all friends that have been connected to this instance.
    """
    return friends_db


@router.post("/friends/add", response_model=Friend)
async def add_friend_by_url(request: AddFriendRequest):
    """
    Add a friend by fetching their instance URL.

    This endpoint proxies the friend request through the backend to avoid CORS issues.
    It fetches the friend's /api/me endpoint, validates the response, and adds them
    to the friends list.
    """
    return await add_verified_friend(request.instance_url)


async def check_one_instance(client: httpx.AsyncClient, instance_url: str) -> InstanceHealth:
    """Check one instance for /health-check. Never raises: failures are reported as offline."""
    try:
        origin = instance_origin(instance_url)
    except ValueError as e:
        logger.warning("✗ Not checking invalid instance URL %r: %r", instance_url, str(e))
        return InstanceHealth(instance_url=instance_url.strip(), is_alive=False, error=f"Invalid URL: {e}")

    parts = urlsplit(origin)
    start_time = time.monotonic()

    def elapsed_ms() -> float:
        return round((time.monotonic() - start_time) * 1000, 2)

    def offline(error: str) -> InstanceHealth:
        logger.warning("✗ %r is OFFLINE - %s", origin, error)
        return InstanceHealth(instance_url=origin, is_alive=False, response_time_ms=elapsed_ms(), error=error)

    try:
        # Workshop domains are trusted; any other host may only resolve to public addresses
        address = None
        if not is_allowed_friend_domain(parts.hostname):
            port = parts.port or (443 if parts.scheme == 'https' else 80)
            address = await resolve_public_address(parts.hostname, port)
        profile = await fetch_profile(client, origin, address)
    except BlockedAddressError:
        return offline("Blocked: not a public address")
    except httpx.HTTPStatusError as e:
        return offline(f"HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        logger.info("Connection to %r failed: %r", origin, e)
        return offline(f"Connection failed: {type(e).__name__}")
    except InvalidProfileError as e:
        return offline(f"Invalid response: {e}")
    except Exception as e:
        logger.exception("Unexpected error while checking %r", origin)
        return offline(f"Error: {type(e).__name__}")

    name = short_text(profile.get('name'), MAX_NAME_LENGTH)
    response_time_ms = elapsed_ms()
    logger.info("✓ %r is ONLINE - Response time: %sms, Name: %r", origin, response_time_ms, name)
    return InstanceHealth(
        instance_url=origin,
        is_alive=True,
        response_time_ms=response_time_ms,
        name=name,
        emoji=short_text(profile.get('emoji'), MAX_EMOJI_LENGTH),
    )


@router.post("/health-check", response_model=List[InstanceHealth])
async def check_instance_health(request: HealthCheckRequest):
    """
    Check the health status of multiple FurNet instances.

    This endpoint proxies health checks through the backend to avoid CORS issues.
    It fetches the /api/me endpoint of every instance concurrently and reports
    whether each one is alive, along with response time metrics. Only the scheme,
    host and port of each URL are used, the number of URLs per request is limited,
    and hosts outside the friend allowlist are only contacted on public addresses.
    """
    logger.info("Starting health check for %d instances", len(request.instance_urls))

    async with httpx.AsyncClient(timeout=5.0) as client:
        results = await asyncio.gather(
            *(check_one_instance(client, url) for url in request.instance_urls)
        )

    online_count = sum(1 for r in results if r.is_alive)
    logger.info("Health check complete: %d online, %d offline out of %d instances",
                online_count, len(results) - online_count, len(results))

    return results
