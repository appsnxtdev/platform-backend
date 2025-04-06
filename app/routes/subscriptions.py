from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database import get_db
from app.services.subscription_service import subscription_service
from app.services.product_service import product_service
from app.models.subscription import Subscription, SubscriptionEvent, SubscriptionStatus, SubscriptionPlan
from app.models.user import User
from app.dependencies.auth import get_current_user, get_admin_user
from app.schemas.dashboard import SubscriptionListItem, DashboardSubscriptionCreate
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionUpdate,
    SubscriptionResponse,
    SubscriptionWithEvents,
    SubscriptionEventResponse,
    ChangeSubscriptionPlan,
    CancelSubscription
)
from loguru import logger

subscription_router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@subscription_router.get("", response_model=List[SubscriptionListItem])
async def get_all_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all subscriptions for the current user in the format expected by the dashboard."""
    try:
        # Get all user's subscriptions
        subscriptions = await subscription_service.get_user_subscriptions(db, current_user.id)
        
        # Format date to "Month DD, YYYY"
        def format_date(date: datetime) -> str:
            if not date:
                return None
            return date.strftime("%B %d, %Y")
        
        # Map plan enum to display name
        def get_plan_display_name(plan: SubscriptionPlan) -> str:
            plan_map = {
                SubscriptionPlan.STARTER: "Starter",
                SubscriptionPlan.PROFESSIONAL: "Professional",
                SubscriptionPlan.ENTERPRISE: "Enterprise"
            }
            return plan_map.get(plan, "Unknown")
        
        # Format subscriptions for the frontend
        formatted_subscriptions = []
        for sub in subscriptions:
            # Calculate remaining days
            remaining_days = 0
            if sub.end_date and sub.status == SubscriptionStatus.ACTIVE:
                delta = sub.end_date - datetime.utcnow()
                remaining_days = max(0, delta.days)
            
            # Get the last event for this subscription
            events = await subscription_service.get_subscription_events(db, sub.id)
            last_event = events[-1] if events else None
            
            # Get product info
            product = await product_service.get_product(db, sub.product_id) if sub.product_id else None
            
            formatted_sub = SubscriptionListItem(
                id=sub.id,
                plan=get_plan_display_name(sub.plan),
                status=sub.status.value,
                startDate=format_date(sub.start_date),
                endDate=format_date(sub.end_date),
                remainingDays=remaining_days,
                autoRenew=sub.auto_renew,
                lastEventDate=format_date(last_event.created_at) if last_event else None,
                lastEventType=last_event.event_type if last_event else None,
                product_id=sub.product_id,
                product_name=product.name if product else "Unknown Product",
                product_slug=product.slug if product else "unknown",
                product_logo=product.logo_url if product else None
            )
            
            formatted_subscriptions.append(formatted_sub)
        
        return formatted_subscriptions
    
    except Exception as e:
        logger.error(f"Error retrieving subscriptions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions"
        )


@subscription_router.get("/{subscription_id}", response_model=SubscriptionResponse)
async def get_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a subscription by ID."""
    subscription = await subscription_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check if user has access to this subscription (owner or admin)
    if subscription.user_id != current_user.id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this subscription"
        )
        
    return subscription


@subscription_router.get("/{subscription_id}/events", response_model=List[SubscriptionEventResponse])
async def get_subscription_events(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all events for a subscription."""
    subscription = await subscription_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check if user has access to this subscription (owner or admin)
    if subscription.user_id != current_user.id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this subscription"
        )
    
    events = await subscription_service.get_subscription_events(db, subscription_id)
    return events


@subscription_router.get("/{subscription_id}/with-events", response_model=SubscriptionWithEvents)
async def get_subscription_with_events(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a subscription with all its events."""
    subscription = await subscription_service.get_subscription(db, subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Check if user has access to this subscription (owner or admin)
    if subscription.user_id != current_user.id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this subscription"
        )
    
    events = await subscription_service.get_subscription_events(db, subscription_id)
    
    # Convert to response model
    subscription_dict = subscription.to_dict()
    subscription_response = SubscriptionResponse(**subscription_dict)
    
    # Create the combined response
    return SubscriptionWithEvents(
        **subscription_response.dict(),
        events=[SubscriptionEventResponse(**event.to_dict()) for event in events]
    )


@subscription_router.get("/user/{user_id}", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all subscriptions for a user."""
    # Check if the requesting user is the owner or an admin
    if current_user.id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access these subscriptions"
        )
        
    subscriptions = await subscription_service.get_user_subscriptions(db, user_id)
    return subscriptions


@subscription_router.get("/user/{user_id}/active", response_model=Optional[SubscriptionResponse])
async def get_user_active_subscription(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the active subscription for a user."""
    # Check if the requesting user is the owner or an admin
    if current_user.id != user_id and not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this subscription"
        )
        
    subscription = await subscription_service.get_active_subscription(db, user_id)
    if not subscription:
        return None
    return subscription


@subscription_router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subscription."""
    try:
        # Check if the user is creating a subscription for themselves or is an admin
        if current_user.id != subscription_data.user_id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create a subscription for another user"
            )
        
        # Verify product exists
        product = await product_service.get_product(db, subscription_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
            
        # Check if product is active
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot subscribe to an inactive product"
            )
            
        # Check if user already has an active subscription for this product
        existing_subscription = await subscription_service.get_user_product_subscription(
            db, 
            subscription_data.user_id, 
            subscription_data.product_id,
            active_only=True
        )
        
        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User already has an active subscription for {product.name}"
            )
        
        # Set the amount based on the selected plan if not provided
        if not subscription_data.amount or subscription_data.amount == 0:
            if subscription_data.plan == SubscriptionPlan.STARTER and product.starter_price:
                subscription_data.amount = product.starter_price
            elif subscription_data.plan == SubscriptionPlan.PROFESSIONAL and product.professional_price:
                subscription_data.amount = product.professional_price
            elif subscription_data.plan == SubscriptionPlan.ENTERPRISE and product.enterprise_price:
                subscription_data.amount = product.enterprise_price
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No pricing defined for plan {subscription_data.plan} on this product"
                )
        
        subscription = await subscription_service.create_subscription(db, subscription_data)
        return subscription
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create subscription: {str(e)}"
        )


@subscription_router.put("/{subscription_id}", response_model=SubscriptionResponse)
async def update_subscription(
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing subscription."""
    try:
        # Get the subscription to check ownership
        subscription = await subscription_service.get_subscription(db, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
            
        # Check permissions (owner or admin)
        if subscription.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this subscription"
            )
        
        updated_subscription = await subscription_service.update_subscription(db, subscription_id, subscription_data)
        return updated_subscription
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to update subscription: {str(e)}"
        )


@subscription_router.post("/{subscription_id}/change-plan", response_model=SubscriptionResponse)
async def change_subscription_plan(
    subscription_id: int,
    plan_data: ChangeSubscriptionPlan,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change a subscription plan."""
    try:
        # Get the subscription to check ownership
        subscription = await subscription_service.get_subscription(db, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
            
        # Check permissions (owner or admin)
        if subscription.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to change this subscription plan"
            )
        
        updated_subscription = await subscription_service.change_subscription_plan(
            db, 
            subscription_id, 
            plan_data.plan, 
            plan_data.prorate
        )
        return updated_subscription
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error changing subscription plan: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to change subscription plan: {str(e)}"
        )


@subscription_router.post("/{subscription_id}/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    subscription_id: int,
    cancellation_data: CancelSubscription,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a subscription."""
    try:
        # Get the subscription to check ownership
        subscription = await subscription_service.get_subscription(db, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
            
        # Check permissions (owner or admin)
        if subscription.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this subscription"
            )
        
        updated_subscription = await subscription_service.cancel_subscription(
            db, 
            subscription_id, 
            cancellation_data.end_immediately,
            cancellation_data.reason
        )
        return updated_subscription
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error canceling subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to cancel subscription: {str(e)}"
        )


@subscription_router.post("/{subscription_id}/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a canceled subscription."""
    try:
        # Get the subscription to check ownership
        subscription = await subscription_service.get_subscription(db, subscription_id)
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
            
        # Check permissions (owner or admin)
        if subscription.user_id != current_user.id and not current_user.is_admin():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to reactivate this subscription"
            )
        
        updated_subscription = await subscription_service.reactivate_subscription(db, subscription_id)
        if not updated_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription cannot be reactivated"
            )
        return updated_subscription
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error reactivating subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reactivate subscription: {str(e)}"
        )


@subscription_router.post("/dashboard", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_dashboard_subscription(
    subscription_data: DashboardSubscriptionCreate,
    current_user: User = Depends(get_admin_user),  # Admin only endpoint
    db: AsyncSession = Depends(get_db)
):
    """Create a subscription from the dashboard (admin only)."""
    try:
        # Verify product exists
        product = await product_service.get_product(db, subscription_data.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
            
        # Check if product is active
        if not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot subscribe to an inactive product"
            )
            
        # Check if user already has an active subscription for this product
        existing_subscription = await subscription_service.get_user_product_subscription(
            db, 
            subscription_data.user_id, 
            subscription_data.product_id,
            active_only=True
        )
        
        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User already has an active subscription for {product.name}"
            )
        
        # Create SubscriptionCreate object from dashboard data
        plan = SubscriptionPlan(subscription_data.plan.value.lower())
        
        # Set amount based on the plan
        amount = 0.0
        if plan == SubscriptionPlan.STARTER and product.starter_price:
            amount = product.starter_price
        elif plan == SubscriptionPlan.PROFESSIONAL and product.professional_price:
            amount = product.professional_price
        elif plan == SubscriptionPlan.ENTERPRISE and product.enterprise_price:
            amount = product.enterprise_price
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No pricing defined for plan {plan} on this product"
            )
            
        # Calculate end date based on billing cycle
        start_date = datetime.utcnow()
        end_date = None
        
        if subscription_data.billing_cycle == "monthly":
            end_date = start_date + timedelta(days=30)
        elif subscription_data.billing_cycle == "quarterly":
            end_date = start_date + timedelta(days=90)
        elif subscription_data.billing_cycle == "yearly":
            end_date = start_date + timedelta(days=365)
        
        # Create subscription data
        create_data = SubscriptionCreate(
            user_id=subscription_data.user_id,
            product_id=subscription_data.product_id,
            plan=plan,
            amount=amount,
            billing_cycle=subscription_data.billing_cycle,
            auto_renew=subscription_data.auto_renew,
            start_date=start_date,
            end_date=end_date,
            payment_provider="manual"  # Dashboard subscriptions are created manually by admin
        )
        
        subscription = await subscription_service.create_subscription(db, create_data)
        return subscription
    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating subscription from dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create subscription: {str(e)}"
        )
