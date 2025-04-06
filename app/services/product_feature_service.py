from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import ProductFeature
from app.models.subscription import SubscriptionPlan
from app.schemas.product import ProductFeatureCreate, ProductFeatureUpdate
from loguru import logger


class ProductFeatureService:
    async def create_feature(self, db: AsyncSession, feature_data: ProductFeatureCreate) -> ProductFeature:
        """Create a new product feature."""
        feature = ProductFeature(
            product_id=feature_data.product_id,
            plan=SubscriptionPlan(feature_data.plan.lower()),
            feature_list=feature_data.feature_list
        )
        db.add(feature)
        await db.commit()
        await db.refresh(feature)
        return feature

    async def get_feature(self, db: AsyncSession, feature_id: int) -> Optional[ProductFeature]:
        """Get a product feature by ID."""
        result = await db.execute(select(ProductFeature).where(ProductFeature.id == feature_id))
        return result.scalar_one_or_none()

    async def get_product_features(self, db: AsyncSession, product_id: int) -> List[ProductFeature]:
        """Get all features for a product."""
        result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.plan)
        )
        return list(result.scalars().all())

    async def get_product_plan_features(
        self, db: AsyncSession, product_id: int, plan: SubscriptionPlan
    ) -> Optional[ProductFeature]:
        """Get features for a specific product and plan."""
        result = await db.execute(
            select(ProductFeature)
            .where(
                ProductFeature.product_id == product_id,
                ProductFeature.plan == plan
            )
        )
        return result.scalar_one_or_none()

    async def update_feature(
        self, db: AsyncSession, feature_id: int, feature_data: ProductFeatureUpdate
    ) -> Optional[ProductFeature]:
        """Update a product feature."""
        feature = await self.get_feature(db, feature_id)
        if not feature:
            return None

        # Update fields if provided
        update_data = feature_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(feature, key, value)

        await db.commit()
        await db.refresh(feature)
        return feature

    async def delete_feature(self, db: AsyncSession, feature_id: int) -> bool:
        """Delete a product feature."""
        feature = await self.get_feature(db, feature_id)
        if not feature:
            return False

        await db.delete(feature)
        await db.commit()
        return True

    async def delete_product_features(self, db: AsyncSession, product_id: int) -> bool:
        """Delete all features for a product."""
        features = await self.get_product_features(db, product_id)
        if not features:
            return False

        for feature in features:
            await db.delete(feature)
        
        await db.commit()
        return True

    async def get_features_by_plan(
        self, db: AsyncSession, product_id: int
    ) -> Dict[str, List[str]]:
        """Get features organized by plan for a product."""
        features = await self.get_product_features(db, product_id)
        
        result = {
            "starter": [],
            "professional": [],
            "enterprise": []
        }
        
        for feature in features:
            plan_name = feature.plan.value
            result[plan_name] = feature.feature_list
        
        return result


# Create service instance
product_feature_service = ProductFeatureService() 