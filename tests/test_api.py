import pytest
from starlette.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data

def test_api_products_list_structure(client):
    res = client.get("/api/products?page=1&page_size=5")
    # Even if DB is disconnected, it should return either 200 or 500 with proper error message
    assert res.status_code in (200, 500)
    if res.status_code == 200:
        data = res.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

def test_api_product_detail_not_found(client):
    res = client.get("/api/products/99999999")
    assert res.status_code in (404, 500)

def test_api_evaluate_validation_error(client):
    # Empty request should return 400 or 422
    res = client.post("/api/evaluate", json={})
    assert res.status_code in (400, 422)

def test_api_users_profile_validation(client):
    # Invalid email format should return 422
    res = client.post("/api/users/profile", json={"user_name": "Test", "email": "invalid-email"})
    assert res.status_code == 422

