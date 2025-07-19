# Basic Tests
import requests

def test_health_check():
    response = requests.get("http://localhost:8000/health")
    assert response.status_code == 200
