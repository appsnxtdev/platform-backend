from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionEvent, SubscriptionStatus, SubscriptionPlan
from app.models.user import User
from app.models.product import Product
from app.schemas.subscription import SubscriptionCreate, SubscriptionUpdate, SubscriptionEventCreate
from loguru import logger


class SubscriptionService:
    """Service for managing subscriptions."""

    @staticmethod
    async def get_subscription(db: AsyncSession, subscription_id: int) -> Optional[Subscription]:
        """Get a subscription by ID."""
        result = await db.execute(select(Subscription).where(Subscription.id == subscription_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_subscriptions(db: AsyncSession, user_id: int) -> List[Subscription]:
        """Get all subscriptions for a user."""
        result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def get_active_subscription(db: AsyncSession, user_id: int) -> Optional[Subscription]:
        """Get the active subscription for a user."""
        result = await db.execute(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            )
            .order_by(Subscription.created_at.desc())
        )
        return result.scalar_one_or_none()
        
    @staticmethod
    async def get_user_product_subscription(
        db: AsyncSession, 
        user_id: int, 
        product_id: int,
        active_only: bool = True
    ) -> Optional[Subscription]:
        """Get a user's subscription for a specific product."""
        query = select(Subscription).where(
            and_(
                Subscription.user_id == user_id,
                Subscription.product_id == product_id
            )
        )
        
        if active_only:
            query = query.where(Subscription.status == SubscriptionStatus.ACTIVE)
            
        result = await db.execute(query.order_by(Subscription.created_at.desc()))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_subscription(db: AsyncSession, subscription_data: SubscriptionCreate) -> Subscription:
        """Create a new subscription."""
        # Verify product exists
        product_result = await db.execute(select(Product).where(Product.id == subscription_data.product_id))
        product = product_result.scalar_one_or_none()
        if not product:
            raise ValueError(f"Product with ID {subscription_data.product_id} not found")
            
        # Check if product is active
        if not product.is_active:
            raise ValueError(f"Product {product.name} is not active")
            
        # Calculate end date based on billing cycle if not provided
        if not subscription_data.end_date and subscription_data.billing_cycle:
            end_date = subscription_data.start_date
            if subscription_data.billing_cycle == "monthly":
                end_date += timedelta(days=30)
            elif subscription_data.billing_cycle == "yearly":
                end_date += timedelta(days=365)
            elif subscription_data.billing_cycle == "quarterly":
                end_date += timedelta(days=90)
            subscription_data.end_date = end_date

        # Create subscription instance
        db_subscription = Subscription(**subscription_data.dict())
        db.add(db_subscription)
        await db.commit()
        await db.refresh(db_subscription)

        # Log subscription creation event
        await SubscriptionService.log_subscription_event(
            db,
            SubscriptionEventCreate(
                subscription_id=db_subscription.id,
                event_type="created",
                description=f"Subscription created for {product.name} with plan {subscription_data.plan}"
            )
        )

        logger.info(f"Created subscription {db_subscription.id} for user {subscription_data.user_id} on product {product.name}")
        return db_subscription

    @staticmethod
    async def update_subscription(
        db: AsyncSession, 
        subscription_id: int, 
        subscription_data: SubscriptionUpdate
    ) -> Optional[Subscription]:
        """Update an existing subscription."""
        db_subscription = await SubscriptionService.get_subscription(db, subscription_id)
        if not db_subscription:
            return None

        # Update subscription with provided data
        update_data = subscription_data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_subscription, key, value)

        # Log subscription update event
        event_description = "Subscription updated"
        if subscription_data.plan:
            event_description += f" - Plan changed to {subscription_data.plan}"
        if subscription_data.status:
            event_description += f" - Status changed to {subscription_data.status}"

        await SubscriptionService.log_subscription_event(
            db,
            SubscriptionEventCreate(
                subscription_id=subscription_id,
                event_type="updated",
                description=event_description
            )
        )

        await db.commit()
        await db.refresh(db_subscription)
        logger.info(f"Updated subscription {subscription_id}")
        return db_subscription

    @staticmethod
    async def change_subscription_plan(
        db: AsyncSession, 
        subscription_id: int, 
        new_plan: SubscriptionPlan, 
        prorate: bool = True
    ) -> Optional[Subscription]:
        """Change a subscription plan."""
        db_subscription = await SubscriptionService.get_subscription(db, subscription_id)
        if not db_subscription:
            return None

        old_plan = db_subscription.plan
        db_subscription.plan = new_plan
        
        # Update amount based on the new plan and product pricing
        product_result = await db.execute(select(Product).where(Product.id == db_subscription.product_id))
        product = product_result.scalar_one_or_none()
        
        if product:
            # Update the amount based on the selected plan
            if new_plan == SubscriptionPlan.STARTER and product.starter_price is not None:
                db_subscription.amount = product.starter_price
            elif new_plan == SubscriptionPlan.PROFESSIONAL and product.professional_price is not None:
                db_subscription.amount = product.professional_price
            elif new_plan == SubscriptionPlan.ENTERPRISE and product.enterprise_price is not None:
                db_subscription.amount = product.enterprise_price

        # Here you would add logic for handling prorating, calculating new amounts, etc.

        # Log plan change event
        await SubscriptionService.log_subscription_event(
            db,
            SubscriptionEventCreate(
                subscription_id=subscription_id,
                event_type="plan_changed",
                description=f"Plan changed from {old_plan} to {new_plan}",
                event_metadata={"prorate": str(prorate), "old_plan": old_plan, "new_plan": new_plan}
            )
        )

        await db.commit()
        await db.refresh(db_subscription)
        logger.info(f"Changed subscription {subscription_id} plan from {old_plan} to {new_plan}")
        return db_subscription

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession, 
        subscription_id: int, 
        end_immediately: bool = False,
        reason: Optional[str] = None
    ) -> Optional[Subscription]:
        """Cancel a subscription."""
        db_subscription = await SubscriptionService.get_subscription(db, subscription_id)
        if not db_subscription:
            return None

        # Set cancellation time
        db_subscription.canceled_at = datetime.utcnow()

        # Update status based on cancellation type
        if end_immediately:
            db_subscription.status = SubscriptionStatus.CANCELED
            db_subscription.end_date = datetime.utcnow()
        else:
            # Will be canceled at the end of the billing period
            db_subscription.status = SubscriptionStatus.ACTIVE

        # Log cancellation event
        await SubscriptionService.log_subscription_event(
            db,
            SubscriptionEventCreate(
                subscription_id=subscription_id,
                event_type="canceled",
                description="Subscription canceled" + (f" - Reason: {reason}" if reason else ""),
                event_metadata={"end_immediately": str(end_immediately), "reason": reason or ""}
            )
        )

        await db.commit()
        await db.refresh(db_subscription)
        logger.info(f"Canceled subscription {subscription_id}")
        return db_subscription

    @staticmethod
    async def reactivate_subscription(db: AsyncSession, subscription_id: int) -> Optional[Subscription]:
        """Reactivate a canceled subscription if within reactivation window."""
        db_subscription = await SubscriptionService.get_subscription(db, subscription_id)
        if not db_subscription or db_subscription.status != SubscriptionStatus.CANCELED:
            return None

        # Check if the subscription is within the reactivation window (e.g., 30 days)
        if db_subscription.canceled_at:
            days_since_cancellation = (datetime.utcnow() - db_subscription.canceled_at).days
            if days_since_cancellation > 30:
                # Beyond reactivation window
                return None

        # Check if the product is still active
        product_result = await db.execute(select(Product).where(Product.id == db_subscription.product_id))
        product = product_result.scalar_one_or_none()
        if not product or not product.is_active:
            raise ValueError(f"Cannot reactivate subscription: product is no longer available")

        # Reactivate the subscription
        db_subscription.status = SubscriptionStatus.ACTIVE
        db_subscription.canceled_at = None

        # Calculate new end date based on reactivation
        if db_subscription.billing_cycle == "monthly":
            db_subscription.end_date = datetime.utcnow() + timedelta(days=30)
        elif db_subscription.billing_cycle == "yearly":
            db_subscription.end_date = datetime.utcnow() + timedelta(days=365)
        elif db_subscription.billing_cycle == "quarterly":
            db_subscription.end_date = datetime.utcnow() + timedelta(days=90)

        # Log reactivation event
        await SubscriptionService.log_subscription_event(
            db,
            SubscriptionEventCreate(
                subscription_id=subscription_id,
                event_type="reactivated",
                description="Subscription reactivated"
            )
        )

        await db.commit()
        await db.refresh(db_subscription)
        logger.info(f"Reactivated subscription {subscription_id}")
        return db_subscription

    @staticmethod
    async def get_subscription_events(db: AsyncSession, subscription_id: int) -> List[SubscriptionEvent]:
        """Get all events for a subscription."""
        result = await db.execute(
            select(SubscriptionEvent)
            .where(SubscriptionEvent.subscription_id == subscription_id)
            .order_by(SubscriptionEvent.created_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def log_subscription_event(
        db: AsyncSession, 
        event_data: SubscriptionEventCreate
    ) -> SubscriptionEvent:
        """Log a subscription event."""
        db_event = SubscriptionEvent(**event_data.dict())
        db.add(db_event)
        await db.commit()
        await db.refresh(db_event)
        return db_event


# Create a singleton instance
subscription_service = SubscriptionService()
