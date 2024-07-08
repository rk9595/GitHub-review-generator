import pytest
from app.main import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200

def test_get_user_repositories(client):
    response = client.get('/api/repositories/octocat')
    assert response.status_code == 200
    assert 'repositories' in response.json

