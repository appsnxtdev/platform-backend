from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.models.base import TimestampedModel


class UserRole(str, enum.Enum):
    """User roles for authorization."""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class UserStatus(str, enum.Enum):
    """User account status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class User(TimestampedModel):
    """User model that extends Supabase Auth user data."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    supabase_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus), default=UserStatus.ACTIVE, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")

    def is_active(self) -> bool:
        """Check if the user is active."""
        return (
            self.status == UserStatus.ACTIVE
            and not self.deleted_at
        )

    def is_admin(self) -> bool:
        """Check if the user is an admin."""
        return self.role == UserRole.ADMIN or self.is_superuser

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        data = super().to_dict()
        return data
