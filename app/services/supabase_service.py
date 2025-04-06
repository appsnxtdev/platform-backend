from typing import Optional, Dict, Any
from supabase import create_client, Client
from app.config import settings
from loguru import logger


class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )

    async def sign_up(
        self,
        email: str,
        password: str,
        user_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sign up a new user with Supabase Auth."""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": user_data.get("full_name") if user_data else None,
                        "company": user_data.get("company") if user_data else None,
                        "phone": user_data.get("phone") if user_data else None
                    }
                }
            })
            logger.info(f"User signed up successfully: {email}")
            return response.user
        except Exception as e:
            logger.error(f"Error signing up user: {str(e)}")
            raise

    async def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in a user with Supabase Auth."""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            logger.info(f"User signed in successfully: {email}")
            return {
                "user": response.user,
                "session": response.session
            }
        except Exception as e:
            logger.error(f"Error signing in user: {str(e)}")
            raise

    async def sign_out(self, access_token: str) -> None:
        """Sign out a user from Supabase Auth."""
        try:
            self.client.auth.sign_out()
            logger.info("User signed out successfully")
        except Exception as e:
            logger.error(f"Error signing out user: {str(e)}")
            raise

    async def get_user(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Supabase Auth."""
        try:
            response = self.client.auth.get_user(access_token)
            return response.user
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            return None

    async def update_user(
        self,
        access_token: str,
        user_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user information in Supabase Auth."""
        try:
            response = self.client.auth.update_user({
                "data": {
                    "full_name": user_data.get("full_name"),
                    "company": user_data.get("company"),
                    "phone": user_data.get("phone")
                }
            })
            logger.info(f"User updated successfully: {user_data.get('email')}")
            return response.user
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            return None

    async def reset_password(self, email: str) -> None:
        """Send password reset email through Supabase Auth."""
        try:
            self.client.auth.reset_password_for_email(email)
            logger.info(f"Password reset email sent to: {email}")
        except Exception as e:
            logger.error(f"Error sending password reset email: {str(e)}")
            raise

    async def verify_email(self, token: str) -> None:
        """Verify user email through Supabase Auth."""
        try:
            self.client.auth.verify_otp({
                "token": token,
                "type": "email"
            })
            logger.info("Email verified successfully")
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            raise

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        try:
            response = self.client.auth.refresh_session(refresh_token)
            logger.info("Token refreshed successfully")
            return response.session
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise

    async def get_user_email(self, access_token: str) -> str:
        """Get the user's email from Supabase using the access token."""
        user_info = self.client.auth.get_user(access_token)
        if user_info and user_info.user:
            return user_info.user.email
        raise ValueError("User not found.")

    async def update_password(self, access_token: str, current_password: str, new_password: str) -> None:
        """Update user password after validating the current password."""
        try:
            # Get the user's email from the access token
            email = await self.get_user_email(access_token)

            # Validate the current password by signing in
            sign_in_response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": current_password
            })

            # Check if the sign-in was successful
            if not sign_in_response.user:
                raise ValueError("Current password is incorrect.")

            # Proceed to update the password
            self.client.auth.update_user({
                "password": new_password
            })

            logger.info("Password updated successfully")
        except Exception as e:
            logger.error(f"Error updating password: {str(e)}")
            raise


# Create a singleton instance
supabase_service = SupabaseService() 