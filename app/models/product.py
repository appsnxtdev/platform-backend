from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Text, Float, JSON, ForeignKey, UniqueConstraint, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TimestampedModel
from app.models.subscription import SubscriptionPlan


class Product(TimestampedModel):
    """SaaS product model for products showcased on the platform."""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    short_description: Mapped[str] = mapped_column(String(255), nullable=False)
    features: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Pricing information
    starter_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    professional_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    enterprise_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Category/tags
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Relationships
    product_features: Mapped[List["ProductFeature"]] = relationship("ProductFeature", back_populates="product", cascade="all, delete-orphan")
    
    def to_dict(self) -> dict:
        """Convert product to dictionary."""
        data = super().to_dict()
        return data


class ProductFeature(TimestampedModel):
    """Features for each product's pricing tier."""
    __tablename__ = "product_features"
    __table_args__ = (
        # Ensure a feature can only be defined once per product and plan
        UniqueConstraint("product_id", "plan", name="uq_product_feature_plan"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan), nullable=False)
    feature_list: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    
    # Relationships
    product = relationship("Product", back_populates="product_features")
    
    def to_dict(self) -> dict:
        """Convert product feature to dictionary."""
        data = super().to_dict()
        return data 