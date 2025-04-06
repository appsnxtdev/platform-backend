from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.product import Product
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.product import ProductCreate, ProductUpdate, PricingTier


class ProductService:
    async def get_product(self, db: AsyncSession, product_id: int) -> Optional[Product]:
        """
        Get a product by ID.
        """
        query = select(Product).where(Product.id == product_id)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_product_by_slug(self, db: AsyncSession, slug: str) -> Optional[Product]:
        """
        Get a product by slug.
        """
        query = select(Product).where(Product.slug == slug)
        result = await db.execute(query)
        return result.scalars().first()

    async def get_products(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        category: Optional[str] = None,
        featured_only: bool = False,
        active_only: bool = True
    ) -> List[Product]:
        """
        Get a list of products with optional filtering.
        """
        query = select(Product)
        
        # Apply filters
        if category:
            query = query.where(Product.category == category)
        if featured_only:
            query = query.where(Product.is_featured == True)
        if active_only:
            query = query.where(Product.is_active == True)
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def create_product(self, db: AsyncSession, product_data: ProductCreate) -> Product:
        """
        Create a new product.
        """
        # Check if slug already exists
        existing = await self.get_product_by_slug(db, product_data.slug)
        if existing:
            raise ValueError(f"Product with slug '{product_data.slug}' already exists")
            
        # Create new product
        product_dict = product_data.model_dump()
        db_product = Product(**product_dict)
        
        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)
        
        logger.info(f"Created new product: {db_product.name} (ID: {db_product.id})")
        return db_product

    async def update_product(
        self, 
        db: AsyncSession, 
        product_id: int, 
        product_data: ProductUpdate
    ) -> Optional[Product]:
        """
        Update an existing product.
        """
        # Get the product
        product = await self.get_product(db, product_id)
        if not product:
            return None
            
        # Check slug uniqueness if it's being updated
        if product_data.slug and product_data.slug != product.slug:
            existing = await self.get_product_by_slug(db, product_data.slug)
            if existing:
                raise ValueError(f"Product with slug '{product_data.slug}' already exists")
        
        # Update the product
        update_data = product_data.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(product, key, value)
            
        await db.commit()
        await db.refresh(product)
        
        logger.info(f"Updated product: {product.name} (ID: {product.id})")
        return product

    async def delete_product(self, db: AsyncSession, product_id: int) -> bool:
        """
        Delete a product.
        """
        product = await self.get_product(db, product_id)
        if not product:
            return False
            
        # Check if there are any subscriptions for this product
        query = select(func.count()).select_from(Subscription).where(Subscription.product_id == product_id)
        result = await db.execute(query)
        count = result.scalar()
        
        if count > 0:
            # Don't delete products with subscriptions
            logger.warning(f"Cannot delete product ID {product_id} - has {count} subscriptions")
            return False
            
        await db.delete(product)
        await db.commit()
        
        logger.info(f"Deleted product: {product.name} (ID: {product.id})")
        return True
        
    async def get_product_pricing_tiers(self, db: AsyncSession, product_id: int) -> List[PricingTier]:
        """
        Get pricing tiers for a product.
        """
        product = await self.get_product(db, product_id)
        if not product:
            return []
            
        pricing_tiers = []
        
        # Create pricing tiers from the product's price fields
        if product.starter_price is not None:
            starter_features = []
            if product.features and isinstance(product.features, dict) and "starter" in product.features:
                starter_features = product.features.get("starter", [])
                
            pricing_tiers.append(PricingTier(
                plan="Starter",
                price=product.starter_price,
                features=starter_features,
                is_popular=False
            ))
            
        if product.professional_price is not None:
            pro_features = []
            if product.features and isinstance(product.features, dict) and "professional" in product.features:
                pro_features = product.features.get("professional", [])
                
            pricing_tiers.append(PricingTier(
                plan="Professional",
                price=product.professional_price,
                features=pro_features,
                is_popular=True  # Usually the professional plan is marked as popular
            ))
            
        if product.enterprise_price is not None:
            enterprise_features = []
            if product.features and isinstance(product.features, dict) and "enterprise" in product.features:
                enterprise_features = product.features.get("enterprise", [])
                
            pricing_tiers.append(PricingTier(
                plan="Enterprise",
                price=product.enterprise_price,
                features=enterprise_features,
                is_popular=False
            ))
            
        return pricing_tiers
        
    async def get_product_stats(self, db: AsyncSession, product_id: int) -> Dict[str, int]:
        """
        Get subscription statistics for a product.
        """
        # Get active subscribers count
        active_query = select(func.count()).select_from(Subscription).where(
            and_(
                Subscription.product_id == product_id,
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        active_result = await db.execute(active_query)
        active_count = active_result.scalar()
        
        # Get total subscribers count
        total_query = select(func.count()).select_from(Subscription).where(
            Subscription.product_id == product_id
        )
        total_result = await db.execute(total_query)
        total_count = total_result.scalar()
        
        return {
            "active_subscribers": active_count,
            "total_subscribers": total_count
        }


# Create a singleton instance
product_service = ProductService() 