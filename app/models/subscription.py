from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, Enum, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TimestampedModel


class SubscriptionStatus(str, enum.Enum):
    """Subscription status."""
    ACTIVE = "active"
    CANCELED = "canceled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
    UNPAID = "unpaid"
    EXPIRED = "expired"


class SubscriptionPlan(str, enum.Enum):
    """Subscription plan types."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class PaymentProvider(str, enum.Enum):
    """Payment provider options."""
    PHONEPE = "phonepe"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    MANUAL = "manual"


class Subscription(TimestampedModel):
    """Subscription model for users."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )
    
    # Pricing and billing details
    amount: Mapped[float] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    
    # Dates
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # External provider details
    payment_provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider),
        default=PaymentProvider.PHONEPE,
        nullable=False
    )
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Features and limits
    max_users: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    max_projects: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    features: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # JSON string of features
    
    # Auto-renewal settings
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")
    product = relationship("Product")  # One-way reference to Product
    subscription_events = relationship("SubscriptionEvent", back_populates="subscription", cascade="all, delete-orphan")
    
    def is_active(self) -> bool:
        """Check if the subscription is active."""
        return (
            self.status in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING] and
            (self.end_date is None or self.end_date > datetime.utcnow())
        )
    
    def is_in_trial(self) -> bool:
        """Check if the subscription is in trial period."""
        return (
            self.status == SubscriptionStatus.TRIALING and 
            self.trial_end_date is not None and 
            self.trial_end_date > datetime.utcnow()
        )
    
    def days_remaining(self) -> int:
        """Calculate days remaining in the subscription."""
        if not self.end_date:
            return 0
        
        delta = self.end_date - datetime.utcnow()
        return max(0, delta.days)
    
    def to_dict(self) -> dict:
        """Convert subscription to dictionary."""
        data = super().to_dict()
        # Fetch product data via relationship
        if self.product:
            data.update({
                "is_active": self.is_active(),
                "is_in_trial": self.is_in_trial(),
                "days_remaining": self.days_remaining(),
                "product_name": self.product.name,
                "product_slug": self.product.slug
            })
        else:
            data.update({
                "is_active": self.is_active(),
                "is_in_trial": self.is_in_trial(),
                "days_remaining": self.days_remaining(),
                "product_name": None,
                "product_slug": None
            })
        return data


class SubscriptionEvent(TimestampedModel):
    """Subscription event history."""
    __tablename__ = "subscription_events"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    event_metadata: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # JSON string of metadata
    
    # Relationships
    subscription = relationship("Subscription", back_populates="subscription_events")
