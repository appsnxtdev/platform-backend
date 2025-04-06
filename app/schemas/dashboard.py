from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from enum import Enum


class UserInfo(BaseModel):
    """User information for dashboard."""
    name: str
    email: str
    company: str = ""
    role: str
    lastLogin: Optional[str] = None


class SubscriptionInfo(BaseModel):
    """Subscription information for dashboard."""
    id: int
    plan: str
    status: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    remainingDays: int = 0
    autoRenew: bool = False


class SubscriptionCounts(BaseModel):
    """Count of subscriptions by plan type."""
    active: int = 0
    starter: int = 0
    professional: int = 0
    enterprise: int = 0


class BillingInfo(BaseModel):
    """Billing information for dashboard."""
    current: float = 0.0
    nextBillingDate: Optional[str] = None


class DashboardStats(BaseModel):
    """Dashboard statistics model."""
    totalSubscriptions: int = 0
    activeSubscriptions: int = 0
    canceledSubscriptions: int = 0
    averageSubscriptionDuration: int = 0
    subscriptions: SubscriptionCounts
    billing: BillingInfo


class DashboardResponse(BaseModel):
    """Complete dashboard response model."""
    stats: DashboardStats


class ProductBasicInfo(BaseModel):
    """Basic product information for dashboard."""
    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None


class SubscriptionPlan(str, Enum):
    """Subscription plan types for dashboard validation."""
    STARTER = "STARTER"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"


class DashboardSubscriptionCreate(BaseModel):
    """Schema for creating a subscription from the dashboard."""
    user_id: int
    product_id: int
    plan: SubscriptionPlan
    billing_cycle: str = "monthly"
    auto_renew: bool = True


class ProductPricingTier(BaseModel):
    """Product pricing tier for dashboard display."""
    plan: str
    price: Optional[float] = None
    features: List[str] = []


class ProductPricingInfo(BaseModel):
    """Complete product pricing information for dashboard."""
    product_id: int
    product_name: str
    product_slug: str
    product_logo: Optional[str] = None
    tiers: List[ProductPricingTier] = []


class SubscriptionListItem(BaseModel):
    """Item in the subscription list."""
    id: int
    plan: str
    status: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    remainingDays: int = 0
    autoRenew: bool = False
    lastEventDate: Optional[str] = None
    lastEventType: Optional[str] = None
    product_id: int
    product_name: str
    product_slug: str
    product_logo: Optional[str] = None