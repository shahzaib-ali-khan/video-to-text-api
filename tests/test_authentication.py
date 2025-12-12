import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_signup_success(api_client: APIClient):
    payload = {
        "username": "alice",
        "email": "alice@example.com",
        "password": "secret123",
    }

    response = api_client.post(reverse("signup"), payload)

    assert response.status_code == 201
    assert response.data["username"] == "alice"
    assert "id" in response.data


@pytest.mark.django_db
def test_signup_invalid(api_client: APIClient):
    response = api_client.post(
        reverse("signup"),
        {
            "username": "bob",
            "email": "bob@example.com",
        },
    )

    assert response.status_code == 400
    assert "password" in response.data


@pytest.mark.django_db
def test_login_success(api_client: APIClient, user):
    response = api_client.post(reverse("login"), {"username": "testuser", "password": "password123"})

    assert response.status_code == 200
    assert response.data["message"] == "Logged in successfully"

    # Session cookie must be set
    assert "sessionid" in response.cookies


@pytest.mark.django_db
def test_login_failure(api_client, user):
    response = api_client.post(reverse("login"), {"username": "alice", "password": "wrongpass"})

    assert response.status_code == 400
    assert "Invalid username or password" in str(response.data)
