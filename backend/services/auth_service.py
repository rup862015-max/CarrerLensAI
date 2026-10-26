"""
Authentication & Authorization Service for CareerLens AI
Provides:
  - Password hashing and verification via bcrypt (salted with 12 rounds)
  - Cryptographically signed JWT access tokens (HS256) with expiration & jti
  - In-memory & database token blocklist for immediate session revocation on logout
  - Sliding-window rate limiting on sensitive authentication routes
  - Generic authentication errors to prevent user enumeration
  - Safe credential handling (zero logging of passwords/tokens)
"""

import os
import re
import time
import uuid
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# Environment configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()

if not JWT_SECRET_KEY:
    if ENVIRONMENT == "production":
        raise RuntimeError("FATAL: JWT_SECRET_KEY environment variable is required in production mode.")
    # Safe fallback secret for local development and test environments
    JWT_SECRET_KEY = "careerlens_dev_jwt_secret_key_fixed_for_local_testing_min32chars!"

JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

logger = logging.getLogger("careerlens.auth")


class AuthError(Exception):
    """Base exception for authentication failures."""
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class TokenExpiredError(AuthError):
    """Raised when an access token has expired."""
    def __init__(self, message: str = "Session expired. Please log in again."):
        super().__init__(message, status_code=401)


class TokenRevokedError(AuthError):
    """Raised when a token has been explicitly revoked via logout."""
    def __init__(self, message: str = "Session has been invalidated. Please log in again."):
        super().__init__(message, status_code=401)


class TokenInvalidError(AuthError):
    """Raised when an access token signature or structure is invalid."""
    def __init__(self, message: str = "Invalid authentication credentials."):
        super().__init__(message, status_code=401)


class RateLimitExceededError(AuthError):
    """Raised when auth attempt rate limit is exceeded."""
    def __init__(self, message: str = "Too many authentication attempts. Please try again in a few moments."):
        super().__init__(message, status_code=429)


# ─── Sliding-Window In-Memory Rate Limiter ───

class SlidingWindowRateLimiter:
    """
    Sliding-window rate limiter to mitigate brute-force password guessing
    and credential stuffing attacks on authentication endpoints.
    """
    def __init__(self):
        self._records: Dict[str, List[float]] = {}

    def check(self, key: str, max_requests: int = 5, window_seconds: int = 60) -> bool:
        """
        Records an attempt and checks if within limit.
        Returns True if within limit, raises RateLimitExceededError if exceeded.
        """
        now = time.time()
        timestamps = self._records.get(key, [])
        # Prune expired timestamps
        timestamps = [t for t in timestamps if now - t < window_seconds]
        if len(timestamps) >= max_requests:
            self._records[key] = timestamps
            raise RateLimitExceededError(
                f"Rate limit exceeded. Maximum {max_requests} attempts per {window_seconds}s. Please wait."
            )
        timestamps.append(now)
        self._records[key] = timestamps
        return True

    def reset(self, key: str):
        """Resets recorded attempts upon successful authentication."""
        self._records.pop(key, None)


rate_limiter = SlidingWindowRateLimiter()

# In-memory revocation cache for fast lookups
_in_memory_revoked_jtis: set = set()


# ─── Password Utilities ───

def hash_password(password: str) -> str:
    """Hashes a password with a fresh random salt using bcrypt (12 rounds)."""
    if not password or len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored bcrypt hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def validate_email_format(email: str) -> bool:
    """Validates standard email format."""
    if not email or len(email) > 254:
        return False
    # RFC 5322 compliant simplified regex
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


# ─── JWT Token Management ───

def create_access_token(
    user_id: str,
    email: str,
    name: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Creates a signed JWT access token with unique jti, expiration, and user claims.
    Returns (token_str, jti, expire_datetime).
    """
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=DEFAULT_EXPIRE_MINUTES)
    expire = now + delta

    payload = {
        "sub": user_id,
        "email": email.strip().lower(),
        "name": name or "",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access"
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, jti, expire


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT access token.
    Verifies signature, expiration, and revocation status.
    """
    if not token:
        raise TokenInvalidError("Missing authentication token.")

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "jti", "iat"]}
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except (jwt.InvalidTokenError, jwt.DecodeError) as e:
        raise TokenInvalidError("Invalid or malformed authentication token.")

    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise TokenRevokedError()

    return payload


# ─── Token Revocation / Logout ───

def revoke_token(jti: str, user_id: str, expires_at: datetime):
    """Revokes a token by adding its jti to the blocklist in-memory and database."""
    _in_memory_revoked_jtis.add(jti)
    try:
        # Import lazily to avoid circular import
        from database import add_token_to_blocklist
        add_token_to_blocklist(jti, user_id, expires_at)
    except Exception as e:
        logger.warning(f"Failed to persist token revocation to database: {e}")


def is_token_revoked(jti: str) -> bool:
    """Checks whether a token jti has been invalidated."""
    if jti in _in_memory_revoked_jtis:
        return True
    try:
        from database import is_token_in_blocklist
        if is_token_in_blocklist(jti):
            _in_memory_revoked_jtis.add(jti)
            return True
    except Exception:
        pass
    return False


def get_test_token(user_id: str = "demo_user", email: str = "candidate@careerlens.ai") -> str:
    """Helper for test suites to generate a valid signed access token."""
    token, _, _ = create_access_token(user_id=user_id, email=email)
    return token
