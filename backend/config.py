from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Only API configuration and instance URL are loaded from environment.
    Animal identity must be configured by editing this file directly.
    """
    # API Configuration (loaded from environment)
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    cors_origins: str = "http://localhost:5173"

    # Instance Configuration (loaded from environment)
    instance_url: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class AnimalConfig:
    """
    Animal identity configuration for this FurNet instance.

    WORKSHOP PARTICIPANTS: Edit these values to personalize your animal!
    These are hardcoded and not loaded from environment variables.
    """
    # Animal Identity - Fixed Fields (Required)
    animal_name: str = "Rusty"
    animal_species: str = "Red Panda"
    animal_description: str = "A curious and playful red panda who loves to explore"

    # Animal Identity - Optional Fields
    animal_habitat: Optional[str] = "Bamboo forests of the Himalayas"
    animal_diet: Optional[str] = "Bamboo, fruits, and occasional insects"
    animal_fun_fact: Optional[str] = "Red pandas use their bushy tails as blankets in cold weather"
    animal_emoji: Optional[str] = "🐼"
    animal_color: Optional[str] = "rust-red"


# Global settings instance
settings = Settings()

# Global animal config instance
animal_config = AnimalConfig()
