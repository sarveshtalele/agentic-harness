"""Fixture for the doc parser and template tests: an authenticated admin client."""
import os

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture
def auth_client():
    with TestClient(app) as test_client:
        login_res = test_client.post(
            "/api/auth/login",
            json={"username": "qa-admin", "password": os.environ["ATLAS_ADMIN_PASSWORD"]}
        )
        assert login_res.status_code == 200
        yield test_client
