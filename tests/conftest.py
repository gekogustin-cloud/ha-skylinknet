"""Shared fixtures for the SkylinkNet tests."""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load the integration from custom_components/."""
    yield


@pytest.fixture
def hub_rows():
    """A full device push, like the cloud sends it (hub + two sensors)."""
    return [
        {"dev_id": "F0000000", "status": 4, "battery": 1},
        {"dev_id": "00000001", "status": 0, "battery": 1},
        {"dev_id": "00000002", "status": 0, "battery": 1},
    ]
