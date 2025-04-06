import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator, Dict, Any

from app.main import app
from app.config import settings
from app.database import get_db, Base
from app.models.user import User, UserRole, UserStatus
from app.models.subscription import Subscription, SubscriptionStatus, SubscriptionPlan, SubscriptionEvent


# Create test database engine
test_engine = create_async_engine(settings.TEST_DATABASE_URI)
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create clean database tables before yielding a session for test."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create a session for testing
    async with TestSessionLocal() as session:
        yield session
        # Clean up after test
        await session.rollback()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an HTTP client for making test requests."""
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Use HTTPX AsyncClient to make requests to FastAPI app
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user in the database."""
    # Create a user
    user = User(
        id=1,
        supabase_id="test-user-id",
        email="test@example.com",
        full_name="Test User",
        company="Test Company",
        role=UserRole.USER,
        status=UserStatus.ACTIVE,
        is_superuser=False,
        last_login_at=datetime.utcnow() - timedelta(days=1)
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Add an access token for testing
    user.access_token = "test-access-token"
    
    # Mock the authentication in app routes
    async def mock_get_current_user():
        return user
    
    app.dependency_overrides[get_db] = lambda: db_session
    
    return user


@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    """Create a test admin user in the database."""
    # Create an admin user
    admin = User(
        id=2,
        supabase_id="test-admin-id",
        email="admin@example.com",
        full_name="Admin User",
        company="Test Company",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        is_superuser=True,
        last_login_at=datetime.utcnow() - timedelta(days=1)
    )
    
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    
    # Add an access token for testing
    admin.access_token = "test-admin-token"
    
    return admin


@pytest.fixture
async def test_subscription(db_session: AsyncSession, test_user: User) -> Subscription:
    """Create a test subscription for the test user."""
    # Create a subscription
    subscription = Subscription(
        id=1,
        user_id=test_user.id,
        plan=SubscriptionPlan.PROFESSIONAL,
        status=SubscriptionStatus.ACTIVE,
        start_date=datetime.utcnow() - timedelta(days=30),
        end_date=datetime.utcnow() + timedelta(days=335),
        auto_renew=True,
        payment_method="credit_card",
        external_id="test-subscription-id"
    )
    
    db_session.add(subscription)
    
    # Create a subscription event
    event = SubscriptionEvent(
        subscription_id=1,
        event_type="created",
        event_metadata={"price": 9.99, "currency": "USD"}
    )
    
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(subscription)
    
    return subscription 