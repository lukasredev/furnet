from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from urllib.parse import urlparse
import httpx
from api.models import Animal, Friend
from config import settings, animal_config

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
