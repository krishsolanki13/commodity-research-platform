from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Fresh TestClient per test. Uses create_app() factory for isolation."""
    return TestClient(create_app())
