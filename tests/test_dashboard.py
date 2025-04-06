import pytest
from fastapi import status
from httpx import AsyncClient
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, MagicMock

from app.models.user import User
from app.models.subscription import Subscription


@pytest.mark.asyncio
async def test_get_dashboard_stats_no_subscription(
    async_client: AsyncClient, 
    db_session: AsyncSession,
    test_user: User
):
    """Test getting dashboard stats when user has no subscriptions."""
    # Setup: No additional setup needed, using test_user fixture
    
    # Make request with auth token
    response = await async_client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    
    # Verify
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "stats" in data
    assert data["stats"]["totalSubscriptions"] == 0
    assert data["stats"]["activeSubscriptions"] == 0
    
    # Verify subscription counts
    assert "subscriptions" in data["stats"]
    assert data["stats"]["subscriptions"]["active"] == 0
    assert data["stats"]["subscriptions"]["starter"] == 0
    assert data["stats"]["subscriptions"]["professional"] == 0
    assert data["stats"]["subscriptions"]["enterprise"] == 0
    
    # Verify billing info
    assert "billing" in data["stats"]
    assert data["stats"]["billing"]["current"] == 0
    assert data["stats"]["billing"]["nextBillingDate"] is None
    
    # Verify userInfo and subscription are not in the response
    assert "userInfo" not in data
    assert "subscription" not in data


@pytest.mark.asyncio
async def test_get_dashboard_stats_with_subscription(
    async_client: AsyncClient, 
    db_session: AsyncSession,
    test_user: User,
    test_subscription: Subscription
):
    """Test getting dashboard stats when user has a subscription."""
    # Setup: Using test_user and test_subscription fixtures
    
    # Make request with auth token
    response = await async_client.get(
        "/api/v1/dashboard/stats",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    
    # Verify
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "stats" in data
    assert data["stats"]["totalSubscriptions"] == 1
    assert data["stats"]["activeSubscriptions"] == 1
    
    # Verify subscription counts
    assert "subscriptions" in data["stats"]
    assert data["stats"]["subscriptions"]["active"] == 1
    assert data["stats"]["subscriptions"]["professional"] == 1  # Test subscription is Professional
    
    # Verify billing info
    assert "billing" in data["stats"]
    assert data["stats"]["billing"]["current"] > 0  # Should have a billing amount
    assert data["stats"]["billing"]["nextBillingDate"] is not None  # Should have a next billing date
    
    # Verify userInfo and subscription are not in the response
    assert "userInfo" not in data
    assert "subscription" not in data


@pytest.mark.asyncio
async def test_get_all_subscriptions_empty(
    async_client: AsyncClient, 
    db_session: AsyncSession,
    test_user: User
):
    """Test getting all subscriptions when user has none."""
    # Setup: No additional setup needed, using test_user fixture
    
    # Make request with auth token
    response = await async_client.get(
        "/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    
    # Verify
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.asyncio
async def test_get_all_subscriptions(
    async_client: AsyncClient, 
    db_session: AsyncSession,
    test_user: User,
    test_subscription: Subscription
):
    """Test getting all subscriptions."""
    # Setup: Using test_user and test_subscription fixtures
    
    # Make request with auth token
    response = await async_client.get(
        "/api/v1/subscriptions",
        headers={"Authorization": f"Bearer {test_user.access_token}"}
    )
    
    # Verify
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    
    sub = data[0]
    assert "id" in sub
    assert "plan" in sub
    assert sub["plan"] in ["Starter", "Professional", "Enterprise"]
    assert "status" in sub
    assert sub["status"] in ["active", "canceled", "expired"]
    assert "startDate" in sub


@pytest.mark.asyncio
async def test_dashboard_unauthorized(async_client: AsyncClient):
    """Test accessing dashboard without authentication."""
    # Make request without auth token
    response = await async_client.get("/api/v1/dashboard/stats")
    
    # Verify
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_subscriptions_unauthorized(async_client: AsyncClient):
    """Test accessing subscriptions without authentication."""
    # Make request without auth token
    response = await async_client.get("/api/v1/subscriptions")
    
    # Verify
    assert response.status_code == status.HTTP_401_UNAUTHORIZED 