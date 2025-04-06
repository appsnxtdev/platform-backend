from fastapi import APIRouter
from app.routes.auth import auth_router
from app.routes.subscriptions import subscription_router
from app.routes.dashboard import dashboard_router
from app.routes.products import product_router

api_router = APIRouter()

# Include auth router
api_router.include_router(auth_router)

# Include subscription router - removing prefix as it's defined in the router itself
api_router.include_router(subscription_router)

# Include dashboard router
api_router.include_router(dashboard_router)

# Include products router
api_router.include_router(product_router)

# Import and include other route modules here
# Example:
# from app.routes import users, auth, etc
# api_router.include_router(users.router, prefix="/users", tags=["users"])
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
