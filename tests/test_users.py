import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.user.schemas import UserCreate
from app.modules.user.service import UserService


@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """Test creating a new user"""
    response = await client.post(
        "/api/v1/users/",
        json={
            "email": "test@example.com",
            "name": "Test User",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["name"] == "Test User"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_duplicate_user(client: AsyncClient):
    """Test creating a user with duplicate email"""
    user_data = {
        "email": "duplicate@example.com",
        "name": "Test User",
        "password": "testpassword123",
    }

    # Create first user
    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 201

    # Try to create duplicate
    response = await client.post("/api/v1/users/", json=user_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_read_users(client: AsyncClient, db_session: AsyncSession):
    """Test reading users list"""
    # Create test users
    user_service = UserService(db_session)
    auth_service = AuthService()
    user1 = UserCreate(email="user1@example.com", name="User 1", password="pass123")
    user2 = UserCreate(email="user2@example.com", name="User 2", password="pass123")
    await user_service.create(user1, auth_service.get_password_hash(user1.password))
    await user_service.create(user2, auth_service.get_password_hash(user2.password))

    response = await client.get("/api/v1/users/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["email"] == "user1@example.com"
    assert data[1]["email"] == "user2@example.com"


@pytest.mark.asyncio
async def test_read_user_by_id(client: AsyncClient, db_session: AsyncSession):
    """Test reading a specific user"""
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(
        email="testuser@example.com", name="Test User", password="pass123"
    )
    created_user = await user_service.create(
        user, auth_service.get_password_hash(user.password)
    )

    response = await client.get(f"/api/v1/users/{created_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["id"] == created_user.id


@pytest.mark.asyncio
async def test_read_user_not_found(client: AsyncClient):
    """Test reading a non-existent user"""
    response = await client.get("/api/v1/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_update_user(client: AsyncClient, db_session: AsyncSession):
    """Test updating a user"""
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(email="update@example.com", name="Old Name", password="pass123")
    created_user = await user_service.create(
        user, auth_service.get_password_hash(user.password)
    )

    response = await client.put(
        f"/api/v1/users/{created_user.id}", json={"name": "New Name"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["email"] == "update@example.com"


@pytest.mark.asyncio
async def test_update_user_not_found(client: AsyncClient):
    """Test updating a non-existent user"""
    response = await client.put("/api/v1/users/999", json={"name": "New Name"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, db_session: AsyncSession):
    """Test deleting a user"""
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(email="delete@example.com", name="Delete Me", password="pass123")
    created_user = await user_service.create(
        user, auth_service.get_password_hash(user.password)
    )

    response = await client.delete(f"/api/v1/users/{created_user.id}")
    assert response.status_code == 204

    # Verify user is deleted
    response = await client.get(f"/api/v1/users/{created_user.id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_user_not_found(client: AsyncClient):
    """Test deleting a non-existent user"""
    response = await client.delete("/api/v1/users/999")
    assert response.status_code == 404
