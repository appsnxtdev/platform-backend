from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.product_service import product_service
from app.services.subscription_service import subscription_service
from app.services.product_feature_service import product_feature_service
from app.models.user import User
from app.models.subscription import SubscriptionPlan
from app.dependencies.auth import get_current_user, get_admin_user
from app.schemas.product import (
    ProductCreate, 
    ProductUpdate, 
    ProductResponse, 
    ProductListItem,
    ProductDetail,
    ProductFeatureCreate
)
from app.schemas.dashboard import ProductPricingInfo, ProductPricingTier
from loguru import logger

product_router = APIRouter(prefix="/products", tags=["products"])


@product_router.get("", response_model=List[ProductListItem])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    featured: bool = False,
    current_user: User = Depends(get_current_user),  # Require authentication
    db: AsyncSession = Depends(get_db)
):
    """Get a list of all products with optional filtering. Requires authentication."""
    try:
        products = await product_service.get_products(
            db=db,
            skip=skip,
            limit=limit,
            category=category,
            featured_only=featured,
            active_only=True  # Only show active products to regular users
        )
        return products
    except Exception as e:
        logger.error(f"Error retrieving products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products"
        )


@product_router.get("/{slug}", response_model=ProductDetail)
async def get_product_by_slug(
    slug: str,
    current_user: User = Depends(get_admin_user),  # Only admins can view detailed product info
    db: AsyncSession = Depends(get_db)
):
    """Get detailed product information by slug (admin only)."""
    try:
        # Get the product
        product = await product_service.get_product_by_slug(db, slug)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
            
        # Get pricing tiers
        pricing_tiers = await product_service.get_product_pricing_tiers(db, product.id)
        
        # Get subscription stats
        stats = await product_service.get_product_stats(db, product.id)
        
        # Prepare the response
        product_dict = product.to_dict()
        product_response = ProductResponse(**product_dict)
        
        # Create detailed response
        detail_response = ProductDetail(
            **product_response.dict(),
            pricing_tiers=pricing_tiers,
            active_subscribers=stats["active_subscribers"],
            total_subscribers=stats["total_subscribers"]
        )
        
        return detail_response
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error retrieving product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product"
        )


@product_router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(get_admin_user),  # Only admins can create products
    db: AsyncSession = Depends(get_db)
):
    """Create a new product (admin only)."""
    try:
        product = await product_service.create_product(db, product_data)
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


@product_router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(get_admin_user),  # Only admins can update products
    db: AsyncSession = Depends(get_db)
):
    """Update an existing product (admin only)."""
    try:
        product = await product_service.update_product(db, product_id, product_data)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@product_router.patch("/{product_id}", response_model=ProductResponse)
async def patch_product(
    product_id: int,
    product_data: ProductUpdate,
    current_user: User = Depends(get_admin_user),  # Only admins can update products
    db: AsyncSession = Depends(get_db)
):
    """Partially update an existing product (admin only)."""
    try:
        # First check if product exists
        existing_product = await product_service.get_product(db, product_id)
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
            
        # Update only the fields provided in the request
        product = await product_service.update_product(db, product_id, product_data)
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error patching product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to patch product"
        )


@product_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    current_user: User = Depends(get_admin_user),  # Only admins can delete products
    db: AsyncSession = Depends(get_db)
):
    """Delete a product (admin only)."""
    try:
        success = await product_service.delete_product(db, product_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete product with active subscriptions"
            )
        return None
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


@product_router.get("/{product_id}/subscriptions", response_model=List[int])
async def get_product_subscription_count(
    product_id: int,
    active_only: bool = Query(True, description="Only count active subscriptions"),
    current_user: User = Depends(get_admin_user),  # Only admins can view all subscriptions
    db: AsyncSession = Depends(get_db)
):
    """Get count of subscriptions for a product (admin only)."""
    try:
        subscriptions = await subscription_service.get_product_subscriptions(
            db, product_id, active_only=active_only
        )
        return [len(subscriptions)]
    except Exception as e:
        logger.error(f"Error getting product subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get product subscriptions"
        )


@product_router.put("/{product_id}/pricing", response_model=ProductPricingInfo)
async def update_product_pricing(
    product_id: int,
    pricing_data: List[ProductPricingTier],
    current_user: User = Depends(get_admin_user),  # Ensure only admins can perform this action
    db: AsyncSession = Depends(get_db)
):
    """Update product pricing information and features (admin only)."""
    try:
        product = await product_service.get_product(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Update product prices
        product_update = ProductUpdate()
        
        for tier in pricing_data:
            plan = tier.plan.lower()
            
            if plan == 'starter':
                product_update.starter_price = tier.price
            elif plan == 'professional':
                product_update.professional_price = tier.price
            elif plan == 'enterprise':
                product_update.enterprise_price = tier.price
                
        # Update the product with new pricing
        updated_product = await product_service.update_product(db, product_id, product_update)
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update product pricing"
            )
            
        # Delete existing features for this product
        await product_feature_service.delete_product_features(db, product_id)
        
        # Add new features from the tiers
        for tier in pricing_data:
            plan_name = tier.plan.lower()
            try:
                plan_enum = SubscriptionPlan(plan_name)
            except ValueError:
                logger.warning(f"Invalid plan name: {plan_name}")
                continue
                
            # Create feature
            if tier.features:
                feature_data = {
                    'product_id': product_id,
                    'plan': plan_enum,
                    'feature_list': tier.features
                }
                
                await product_feature_service.create_feature(
                    db, 
                    ProductFeatureCreate(**feature_data)
                )
        
        # Get the updated product with features for the response
        features_by_plan = await product_feature_service.get_features_by_plan(db, product_id)
        
        # Create pricing tiers response
        tiers = [
            ProductPricingTier(
                plan="Starter",
                price=updated_product.starter_price,
                features=features_by_plan.get("starter", [])
            ),
            ProductPricingTier(
                plan="Professional",
                price=updated_product.professional_price,
                features=features_by_plan.get("professional", [])
            ),
            ProductPricingTier(
                plan="Enterprise",
                price=updated_product.enterprise_price,
                features=features_by_plan.get("enterprise", [])
            )
        ]
        
        # Create minimal response with only relevant product details
        return ProductPricingInfo(
            product_id=updated_product.id,
            product_name=updated_product.name,
            product_slug=updated_product.slug,
            product_logo=updated_product.logo_url,
            tiers=tiers
        )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating product pricing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update product pricing: {str(e)}"
        )


@product_router.patch("/{product_id}/pricing", response_model=ProductPricingInfo)
async def patch_product_pricing(
    product_id: int,
    pricing_data: List[ProductPricingTier],
    current_user: User = Depends(get_admin_user),  # Ensure only admins can perform this action
    db: AsyncSession = Depends(get_db)
):
    """Partially update product pricing information and features (admin only)."""
    try:
        product = await product_service.get_product(db, product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Update product prices if provided
        product_update = ProductUpdate()
        
        for tier in pricing_data:
            plan = tier.plan.lower()
            
            if tier.price is not None:
                if plan == 'starter':
                    product_update.starter_price = tier.price
                elif plan == 'professional':
                    product_update.professional_price = tier.price
                elif plan == 'enterprise':
                    product_update.enterprise_price = tier.price
                
        # Update the product with new pricing
        if product_update.dict(exclude_unset=True):
            updated_product = await product_service.update_product(db, product_id, product_update)
            if not updated_product:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update product pricing"
                )
        else:
            updated_product = product
            
        # Update features for specified tiers
        for tier in pricing_data:
            plan_name = tier.plan.lower()
            try:
                plan_enum = SubscriptionPlan(plan_name)
            except ValueError:
                logger.warning(f"Invalid plan name: {plan_name}")
                continue
                
            # Delete existing features for this plan
            existing_feature = await product_feature_service.get_product_plan_features(db, product_id, plan_enum)
            if existing_feature:
                await product_feature_service.delete_feature(db, existing_feature.id)
                
            # Create feature
            if tier.features:
                feature_data = {
                    'product_id': product_id,
                    'plan': plan_enum,
                    'feature_list': tier.features
                }
                
                await product_feature_service.create_feature(
                    db, 
                    ProductFeatureCreate(**feature_data)
                )
        
        # Get the updated product with features for the response
        features_by_plan = await product_feature_service.get_features_by_plan(db, product_id)
        
        # Create pricing tiers response
        tiers = [
            ProductPricingTier(
                plan="Starter",
                price=updated_product.starter_price,
                features=features_by_plan.get("starter", [])
            ),
            ProductPricingTier(
                plan="Professional",
                price=updated_product.professional_price,
                features=features_by_plan.get("professional", [])
            ),
            ProductPricingTier(
                plan="Enterprise",
                price=updated_product.enterprise_price,
                features=features_by_plan.get("enterprise", [])
            )
        ]
        
        # Create minimal response with only relevant product details
        return ProductPricingInfo(
            product_id=updated_product.id,
            product_name=updated_product.name,
            product_slug=updated_product.slug,
            product_logo=updated_product.logo_url,
            tiers=tiers
        )
            
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error patching product pricing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to patch product pricing: {str(e)}"
        )


@product_router.get("/{product_id}/pricing", response_model=ProductPricingInfo)
async def get_product_pricing(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get product pricing information with features for dashboard display."""
    product = await product_service.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Get features organized by plan
    features_by_plan = await product_feature_service.get_features_by_plan(db, product_id)
    
    # Create pricing tiers
    tiers = [
        ProductPricingTier(
            plan="Starter",
            price=product.starter_price,
            features=features_by_plan.get("starter", [])
        ),
        ProductPricingTier(
            plan="Professional",
            price=product.professional_price,
            features=features_by_plan.get("professional", [])
        ),
        ProductPricingTier(
            plan="Enterprise",
            price=product.enterprise_price,
            features=features_by_plan.get("enterprise", [])
        )
    ]
    
    # Create minimal response with only relevant product details
    return ProductPricingInfo(
        product_id=product.id,
        product_name=product.name,
        product_slug=product.slug,
        product_logo=product.logo_url,
        tiers=tiers
    ) 