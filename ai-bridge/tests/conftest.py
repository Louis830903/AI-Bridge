"""AI-Bridge test configuration."""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Sample configuration for tests."""
    return {
        "chrome": {
            "enabled": True,
            "cdp_url": "http://localhost:9222",
        },
        "feishu": {
            "enabled": True,
            "app_id": "test_app_id",
            "app_secret": "test_secret",
        },
    }
