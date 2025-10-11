from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class Friend(BaseModel):
    """
    Friend connection model for FurNet instances.

    Represents a friend relationship between this instance and another FurNet instance.
    Stores the unique identifier (DNS name + animal name) along with metadata.
    """
    unique_id: str = Field(..., description="Unique identifier (DNS name:animal name)")
    dns_name: str = Field(..., description="DNS hostname of the friend instance")
    name: str = Field(..., description="Animal name of the friend")
    connected_at: datetime = Field(default_factory=datetime.utcnow, description="When the friendship was established")

    class Config:
        json_schema_extra = {
            "example": {
                "unique_id": "furnet-friend.example.com:buddy",
                "dns_name": "furnet-friend.example.com",
                "name": "Buddy",
                "connected_at": "2025-10-11T12:00:00Z"
            }
        }


class Animal(BaseModel):
    """
    Animal identity model for FurNet instances.

    Each FurNet instance represents a participant with an animal identity.
    Fixed fields are required, optional fields can be customized.
    """
    # Fixed required fields
    id: str = Field(..., description="Unique identifier for this instance (DNS name + animal name)")
    name: str = Field(..., description="The animal's name")
    species: str = Field(..., description="The type of animal (e.g., 'Red Panda', 'Arctic Fox')")
    description: str = Field(..., description="A brief description of this animal")
    instance_url: str = Field(..., description="The URL where this FurNet instance is hosted")

    # Optional fields - can be customized per instance
    habitat: Optional[str] = Field(None, description="Where this animal lives")
    diet: Optional[str] = Field(None, description="What this animal eats")
    fun_fact: Optional[str] = Field(None, description="An interesting fact about this animal")
    emoji: Optional[str] = Field(None, description="Emoji representation of the animal")
    color: Optional[str] = Field(None, description="Primary color associated with this animal")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "furnet-workshop.example.com:rusty",
                "name": "Rusty",
                "species": "Red Panda",
                "description": "A curious and playful red panda who loves to explore",
                "instance_url": "https://furnet-workshop.example.com",
                "habitat": "Bamboo forests of the Himalayas",
                "diet": "Bamboo, fruits, and occasional insects",
                "fun_fact": "Red pandas use their bushy tails as blankets in cold weather",
                "emoji": "🐼",
                "color": "rust-red"
            }
        }
