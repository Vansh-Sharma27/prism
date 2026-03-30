"""
User and authentication models.
"""

from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db

MAX_FAILED_LOGINS = 5
LOCKOUT_DURATION_MINUTES = 15


class User(db.Model):
    """Application user for dashboard and APIs."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if self.locked_until is None:
            return False
        return datetime.utcnow() < self.locked_until

    def record_failed_login(self) -> None:
        """Increment failed login counter and lock if threshold exceeded."""
        from datetime import timedelta

        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= MAX_FAILED_LOGINS:
            self.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)

    def reset_failed_logins(self) -> None:
        """Reset failed login counter on successful login."""
        self.failed_login_count = 0
        self.locked_until = None

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
