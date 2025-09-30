import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.service import AuthService
from app.modules.user.schemas import UserCreate
from app.modules.user.service import UserService


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful login"""
    # Create user
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(
        email="login@example.com", name="Login User", password="testpassword"
    )
    await user_service.create(user, auth_service.get_password_hash(user.password))

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """Test login with wrong password"""
    # Create user
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(
        email="wrongpass@example.com", name="User", password="correctpassword"
    )
    await user_service.create(user, auth_service.get_password_hash(user.password))

    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user"""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "somepassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, db_session: AsyncSession):
    """Test getting current user info"""
    # Create user
    user_service = UserService(db_session)
    auth_service = AuthService()
    user = UserCreate(
        email="current@example.com", name="Current User", password="testpassword"
    )
    await user_service.create(user, auth_service.get_password_hash(user.password))

    # Login
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "current@example.com", "password": "testpassword"},
    )
    token = login_response.json()["access_token"]

    # Get current user
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"
    assert data["name"] == "Current User"


@pytest.mark.asyncio
async def test_get_current_user_no_token(client: AsyncClient):
    """Test getting current user without token"""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test getting current user with invalid token"""
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
