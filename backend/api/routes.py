from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from urllib.parse import urlparse
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
