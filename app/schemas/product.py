from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.schemas.subscription import SubscriptionPlanEnum


class ProductFeatureBase(BaseModel):
    """Base schema for product feature."""
    feature_list: List[str]


class ProductFeatureCreate(ProductFeatureBase):
    """Schema for creating a product feature."""
    product_id: int
    plan: SubscriptionPlanEnum


class ProductFeatureUpdate(ProductFeatureBase):
    """Schema for updating a product feature."""
    feature_list: Optional[List[str]] = None


class ProductFeatureResponse(ProductFeatureBase):
    """Schema for product feature response."""
    id: int
    product_id: int
    plan: str
    
    class Config:
        orm_mode = True


class ProductBase(BaseModel):
    """Base schema for SaaS product data."""
    name: str
    slug: str
    description: str
    short_description: str
    features: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    starter_price: Optional[float] = None
    professional_price: Optional[float] = None
    enterprise_price: Optional[float] = None
    is_active: bool = True
    is_featured: bool = False
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ProductCreate(ProductBase):
    """Schema for creating a new SaaS product."""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a SaaS product."""
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    website_url: Optional[str] = None
    starter_price: Optional[float] = None
    professional_price: Optional[float] = None
    enterprise_price: Optional[float] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class ProductResponse(ProductBase):
    """Schema for product response data."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ProductListItem(BaseModel):
    """Schema for product list item displayed to authenticated users."""
    id: int
    name: str
    slug: str
    short_description: str
    logo_url: Optional[str] = None
    category: Optional[str] = None
    is_featured: bool
    starter_price: Optional[float] = None
    professional_price: Optional[float] = None
    enterprise_price: Optional[float] = None
    website_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class PricingTier(BaseModel):
    """Schema for product pricing tiers."""
    plan: str
    price: float
    features: List[str]
    is_popular: bool = False


class ProductDetail(ProductResponse):
    """Schema for detailed product information."""
    pricing_tiers: List[PricingTier] = []
    active_subscribers: int = 0
    total_subscribers: int = 0 