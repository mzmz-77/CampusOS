import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    app = create_app('sqlite://')
    with TestClient(app) as client: yield client
    app.state.engine.dispose()
