"""
Tests for the app-level endpoints, the animal identity and the settings.

Workshop participants edit AnimalConfig, so these tests read the expected values
from it instead of hardcoding the default red panda.
"""
import pytest

from api.routes import generate_animal_id
from config import Settings, animal_config, settings


@pytest.mark.parametrize("path, expected", [
    ("/", {"message": "Welcome to FurNet API"}),
    ("/health", {"status": "healthy"}),
    ("/health/live", {"status": "alive"}),
    ("/health/ready", {"status": "ready"}),
])
def test_root_and_health_endpoints(client, path, expected):
    response = client.get(path)

    assert response.status_code == 200
    assert response.json() == expected


def test_me_returns_the_configured_animal(client):
    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json() == {
        "id": generate_animal_id(settings.instance_url, animal_config.animal_name),
        "name": animal_config.animal_name,
        "species": animal_config.animal_species,
        "description": animal_config.animal_description,
        "instance_url": settings.instance_url,
        "habitat": animal_config.animal_habitat,
        "diet": animal_config.animal_diet,
        "fun_fact": animal_config.animal_fun_fact,
        "emoji": animal_config.animal_emoji,
        "color": animal_config.animal_color,
    }


def test_me_builds_id_from_instance_host_and_animal_name(client, monkeypatch):
    monkeypatch.setattr(settings, "instance_url", "http://localhost:8080")
    monkeypatch.setattr(animal_config, "animal_name", "Mr Fluffy")

    body = client.get("/api/me").json()

    assert body["id"] == "localhost:mr-fluffy"
    assert body["instance_url"] == "http://localhost:8080"


def test_me_allows_optional_fields_to_be_empty(client, monkeypatch):
    for field in ("animal_habitat", "animal_diet", "animal_fun_fact", "animal_emoji", "animal_color"):
        monkeypatch.setattr(animal_config, field, None)

    body = client.get("/api/me").json()

    assert [body[key] for key in ("habitat", "diet", "fun_fact", "emoji", "color")] == [None] * 5


@pytest.mark.parametrize("instance_url, animal_name, expected", [
    ("https://furnet.lukasre.ch", "Rusty", "furnet.lukasre.ch:rusty"),
    ("http://localhost:8000", "Rusty", "localhost:rusty"),
    ("https://x.vsos.ethz.ch:8443/", "Rusty", "x.vsos.ethz.ch:rusty"),
    ("furnet.lukasre.ch", "Rusty", "furnet.lukasre.ch:rusty"),
    ("https://x.vsos.ethz.ch", "Big Red Panda", "x.vsos.ethz.ch:big-red-panda"),
])
def test_generate_animal_id(instance_url, animal_name, expected):
    assert generate_animal_id(instance_url, animal_name) == expected


def test_settings_default_instance_url(monkeypatch):
    monkeypatch.delenv("INSTANCE_URL", raising=False)

    assert Settings(_env_file=None).instance_url == "http://localhost:8000"


def test_settings_read_instance_url_from_environment(monkeypatch):
    monkeypatch.setenv("INSTANCE_URL", "https://zoo.vsos.ethz.ch")

    assert Settings(_env_file=None).instance_url == "https://zoo.vsos.ethz.ch"
