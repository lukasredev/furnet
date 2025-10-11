from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from urllib.parse import urlparse
import httpx
import time
import logging
from api.models import Animal, Friend
from config import settings, animal_config

logger = logging.getLogger(__name__)

router = APIRouter()


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

# Request model for adding friends by URL
class AddFriendRequest(BaseModel):
    instance_url: str

# Request model for health check
class HealthCheckRequest(BaseModel):
    instance_urls: List[str]

# Response model for health check
class InstanceHealth(BaseModel):
    instance_url: str
    is_alive: bool
    response_time_ms: float | None = None
    error: str | None = None
    name: str | None = None
    emoji: str | None = None

# Sample data model
class Item(BaseModel):
    id: int
    name: str
    description: str | None = None

# In-memory storage for demo purposes
items_db: List[Item] = [
    Item(id=1, name="Item 1", description="First item"),
    Item(id=2, name="Item 2", description="Second item"),
]

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

@router.get("/items", response_model=List[Item])
async def get_items():
    """Get all items"""
    return items_db

@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get a specific item by ID"""
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@router.post("/items", response_model=Item)
async def create_item(item: Item):
    """Create a new item"""
    items_db.append(item)
    return item

@router.delete("/items/{item_id}")
async def delete_item(item_id: int):
    """Delete an item"""
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db.pop(i)
            return {"message": "Item deleted"}
    raise HTTPException(status_code=404, detail="Item not found")


# Friend connection endpoints
@router.post("/friends", response_model=Friend)
async def add_friend(friend: Friend):
    """
    Add a friend connection to this FurNet instance.

    Accepts a friend's unique identifier (DNS name + animal name) and stores
    the friendship connection in memory.
    """
    # Check if friend already exists
    for existing_friend in friends_db:
        if existing_friend.unique_id == friend.unique_id:
            raise HTTPException(
                status_code=400,
                detail=f"Friend with unique_id '{friend.unique_id}' already exists"
            )

    # Check if we've reached the maximum number of friends (1000)
    if len(friends_db) >= 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum number of friends (1000) reached. Cannot add more friends."
        )

    # Validate that the friend is from the allowed domain (vsos.ethz.ch)
    if not friend.dns_name.endswith('vsos.ethz.ch'):
        raise HTTPException(
            status_code=403,
            detail=f"Friends must be from the vsos.ethz.ch domain. Got: {friend.dns_name}"
        )

    # Add friend to in-memory storage
    friends_db.append(friend)
    return friend


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
    # Normalize the instance URL
    friend_instance_url = request.instance_url.strip()
    if not friend_instance_url.startswith('http://') and not friend_instance_url.startswith('https://'):
        friend_instance_url = 'https://' + friend_instance_url

    # Remove trailing slash if present
    friend_instance_url = friend_instance_url.rstrip('/')

    # Construct the /api/me endpoint URL
    friend_me_url = f"{friend_instance_url}/api/me"

    try:
        # Fetch friend's profile from their instance
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(friend_me_url)
            response.raise_for_status()
            friend_data = response.json()

        # Validate that we got the expected fields
        if not all(key in friend_data for key in ['id', 'name', 'instance_url']):
            raise HTTPException(
                status_code=400,
                detail="Invalid response from friend instance - missing required fields"
            )

        # Get our own animal ID to prevent self-friending
        our_id = generate_animal_id(settings.instance_url, animal_config.animal_name)

        # Check if trying to add yourself as a friend
        if friend_data['id'] == our_id:
            raise HTTPException(
                status_code=400,
                detail="You can't add yourself as a friend!"
            )

        # Check if friend already exists
        for existing_friend in friends_db:
            if existing_friend.unique_id == friend_data['id']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Friend with unique_id '{friend_data['id']}' already exists"
                )

        # Check if we've reached the maximum number of friends (1000)
        if len(friends_db) >= 1000:
            raise HTTPException(
                status_code=400,
                detail="Maximum number of friends (1000) reached. Cannot add more friends."
            )

        # Extract DNS name from the friend's instance URL
        parsed = urlparse(friend_data['instance_url'])
        dns_name = parsed.netloc if parsed.netloc else parsed.path
        # Remove port if present
        dns_name = dns_name.split(':')[0] if ':' in dns_name else dns_name

        # Validate that the friend is from the allowed domain (vsos.ethz.ch)
        if not dns_name.endswith('vsos.ethz.ch'):
            raise HTTPException(
                status_code=403,
                detail=f"Friends must be from the vsos.ethz.ch domain. Got: {dns_name}"
            )

        # Create and add the friend
        new_friend = Friend(
            unique_id=friend_data['id'],
            dns_name=dns_name,
            name=friend_data['name']
        )

        friends_db.append(new_friend)
        return new_friend

    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch friend's profile from {friend_me_url}. Status: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to friend instance: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while adding friend: {str(e)}"
        )


@router.post("/health-check", response_model=List[InstanceHealth])
async def check_instance_health(request: HealthCheckRequest):
    """
    Check the health status of multiple FurNet instances.

    This endpoint proxies health checks through the backend to avoid CORS issues.
    It attempts to fetch the /api/me endpoint from each instance and reports
    whether the instance is alive, along with response time metrics.
    """
    logger.info(f"Starting health check for {len(request.instance_urls)} instances")
    results = []

    async with httpx.AsyncClient(timeout=5.0) as client:
        for instance_url in request.instance_urls:
            # Normalize the instance URL
            normalized_url = instance_url.strip()
            if not normalized_url.startswith('http://') and not normalized_url.startswith('https://'):
                normalized_url = 'https://' + normalized_url

            # Remove trailing slash if present
            normalized_url = normalized_url.rstrip('/')

            # Construct the /api/me endpoint URL
            health_check_url = f"{normalized_url}/api/me"
            logger.info(f"Checking health for: {normalized_url} (URL: {health_check_url})")

            start_time = time.time()

            try:
                response = await client.get(health_check_url)
                response.raise_for_status()

                # Calculate response time in milliseconds
                response_time_ms = (time.time() - start_time) * 1000

                # Extract name and emoji from response
                data = response.json()
                animal_name = data.get('name', None)
                animal_emoji = data.get('emoji', None)

                logger.info(f"✓ {normalized_url} is ONLINE - Response time: {round(response_time_ms, 2)}ms, Name: {animal_name}")
                logger.info(f"  Response data: {data}")

                results.append(InstanceHealth(
                    instance_url=normalized_url,
                    is_alive=True,
                    response_time_ms=round(response_time_ms, 2),
                    error=None,
                    name=animal_name,
                    emoji=animal_emoji
                ))

            except httpx.HTTPStatusError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"HTTP {e.response.status_code}"
                logger.warning(f"✗ {normalized_url} is OFFLINE - {error_msg}")
                results.append(InstanceHealth(
                    instance_url=normalized_url,
                    is_alive=False,
                    response_time_ms=round(response_time_ms, 2),
                    error=error_msg,
                    name=None,
                    emoji=None
                ))

            except httpx.RequestError as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"Connection failed: {type(e).__name__}"
                logger.warning(f"✗ {normalized_url} is OFFLINE - {error_msg}: {str(e)}")
                results.append(InstanceHealth(
                    instance_url=normalized_url,
                    is_alive=False,
                    response_time_ms=round(response_time_ms, 2),
                    error=error_msg,
                    name=None,
                    emoji=None
                ))

            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                error_msg = f"Error: {type(e).__name__}"
                logger.error(f"✗ {normalized_url} is OFFLINE - Unexpected error: {str(e)}")
                results.append(InstanceHealth(
                    instance_url=normalized_url,
                    is_alive=False,
                    response_time_ms=round(response_time_ms, 2),
                    error=error_msg,
                    name=None,
                    emoji=None
                ))

    online_count = sum(1 for r in results if r.is_alive)
    offline_count = len(results) - online_count
    logger.info(f"Health check complete: {online_count} online, {offline_count} offline out of {len(results)} instances")

    return results
