from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.services.subscription_service import subscription_service
from app.models.subscription import SubscriptionStatus, SubscriptionPlan
from app.schemas.dashboard import DashboardResponse, UserInfo, SubscriptionInfo, DashboardStats, SubscriptionCounts, BillingInfo
from loguru import logger

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for the current user."""
    try:
        # Get user's active subscription (if any)
        active_subscription = await subscription_service.get_active_subscription(db, current_user.id)
        
        # Get all user's subscriptions for stats
        all_subscriptions = await subscription_service.get_user_subscriptions(db, current_user.id)
        
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
        
        # Count subscriptions by plan type
        subscription_counts = SubscriptionCounts(
            active=sum(1 for sub in all_subscriptions if sub.status == SubscriptionStatus.ACTIVE),
            starter=sum(1 for sub in all_subscriptions if sub.plan == SubscriptionPlan.STARTER),
            professional=sum(1 for sub in all_subscriptions if sub.plan == SubscriptionPlan.PROFESSIONAL),
            enterprise=sum(1 for sub in all_subscriptions if sub.plan == SubscriptionPlan.ENTERPRISE)
        )
        
        # Prepare billing information
        billing_info = BillingInfo(
            current=0.0,
            nextBillingDate=None
        )
        
        # If there's an active subscription, update billing info
        if active_subscription:
            # Get the subscription's billing amount (this would come from payment events or a pricing table)
            # For now using placeholder values based on plan
            if active_subscription.plan == SubscriptionPlan.STARTER:
                billing_amount = 9.99
            elif active_subscription.plan == SubscriptionPlan.PROFESSIONAL:
                billing_amount = 29.99
            elif active_subscription.plan == SubscriptionPlan.ENTERPRISE:
                billing_amount = 99.99
            else:
                billing_amount = 0.0
            
            # Update billing info
            billing_info.current = billing_amount
            
            # Next billing date would typically be calculated from the start date and billing cycle
            # For simplicity, if end_date exists, use that, otherwise use 30 days from now
            if active_subscription.end_date:
                billing_info.nextBillingDate = format_date(active_subscription.end_date)
            else:
                next_billing_date = datetime.utcnow() + timedelta(days=30)
                billing_info.nextBillingDate = format_date(next_billing_date)
        
        # Prepare stats
        stats = DashboardStats(
            totalSubscriptions=len(all_subscriptions),
            activeSubscriptions=subscription_counts.active,
            canceledSubscriptions=sum(1 for sub in all_subscriptions if sub.status == SubscriptionStatus.CANCELED),
            averageSubscriptionDuration=0,  # Will calculate below if applicable
            subscriptions=subscription_counts,
            billing=billing_info
        )
        
        # Calculate average subscription duration if there are any subscriptions
        if all_subscriptions:
            total_duration = 0
            count = 0
            
            for sub in all_subscriptions:
                if sub.start_date:
                    end = sub.end_date if sub.end_date else datetime.utcnow()
                    duration = (end - sub.start_date).days
                    total_duration += duration
                    count += 1
            
            if count > 0:
                stats.averageSubscriptionDuration = round(total_duration / count)
        
        # Create the response with just the stats
        response = DashboardResponse(stats=stats)
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving dashboard stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard statistics"
        ) 