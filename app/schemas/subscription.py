from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class SubscriptionStatus(str, Enum):
    """Subscription status enum for schema validation."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    UNPAID = "unpaid"
    EXPIRED = "expired"


class SubscriptionPlan(str, Enum):
    """Subscription plan types for schema validation."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


# Alias for external imports to match the model's enum
SubscriptionPlanEnum = SubscriptionPlan


class PaymentProvider(str, Enum):
    """Payment provider options for schema validation."""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    PHONEPE = "phonepe"
    MANUAL = "manual"


class SubscriptionBase(BaseModel):
    """Base schema for subscription data."""
    product_id: int
    plan: SubscriptionPlan
    amount: float
    currency: str = "INR"
    billing_cycle: str = "monthly"
    auto_renew: bool = True
    max_users: int = 1
    max_projects: Optional[int] = None
    features: Optional[str] = None
    payment_provider: PaymentProvider = PaymentProvider.PHONEPE


class SubscriptionCreate(SubscriptionBase):
    """Schema for creating a new subscription."""
    user_id: int
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    provider_subscription_id: Optional[str] = None
    provider_customer_id: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    """Schema for updating an existing subscription."""
    plan: Optional[SubscriptionPlan] = None
    status: Optional[SubscriptionStatus] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    max_users: Optional[int] = None
    max_projects: Optional[int] = None
    features: Optional[str] = None
    auto_renew: Optional[bool] = None
    provider_subscription_id: Optional[str] = None
    provider_customer_id: Optional[str] = None


class SubscriptionEventCreate(BaseModel):
    """Schema for creating a subscription event."""
    subscription_id: int
    event_type: str
    description: Optional[str] = None
    event_metadata: Optional[str] = None


class SubscriptionEventResponse(BaseModel):
    """Schema for subscription event response."""
    id: int
    subscription_id: int
    event_type: str
    description: Optional[str] = None
    event_metadata: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductInfo(BaseModel):
    """Schema for basic product information in subscription responses."""
    id: int
    name: str
    slug: str
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True


class SubscriptionResponse(SubscriptionBase):
    """Schema for subscription response."""
    id: int
    user_id: int
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    provider_subscription_id: Optional[str] = None
    provider_customer_id: Optional[str] = None
    is_active: bool
    is_in_trial: bool
    days_remaining: int
    product: ProductInfo
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionWithEvents(SubscriptionResponse):
    """Schema for subscription with events."""
    events: List[SubscriptionEventResponse] = []


class ChangeSubscriptionPlan(BaseModel):
    """Schema for changing subscription plan."""
    plan: SubscriptionPlan
    prorate: bool = True


class CancelSubscription(BaseModel):
    """Schema for canceling a subscription."""
    end_immediately: bool = False
    reason: Optional[str] = None
