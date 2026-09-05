"""
Authentication for AgentTrust.

This is the single place that verifies the Clerk token your frontend sends
with every API call. Any route that needs a logged-in merchant can add:

    merchant_id: str = Depends(get_current_merchant_id)

and FastAPI will make sure the request has a valid token before the route runs.
"""
from typing import Optional
from fastapi import Header, HTTPException
from clerk_backend_api.security import (
    verify_token,
    VerifyTokenOptions,
    TokenVerificationError,
)
import config


def get_demo_merchant_id() -> str:
    """
    Returns the tenant used for unauthenticated / demo requests (local storefront).
    This keeps the no-login storefront working while authenticated merchants stay
    strictly scoped to their own Clerk user ID.
    """
    return "demo"


def get_current_merchant_id(authorization: str = Header(None)) -> str:
    """
    FastAPI dependency.

    Expects a header like:  Authorization: Bearer <Clerk session token>

    Returns the merchant's Clerk user ID (the "sub" claim of the JWT),
    or raises a clear 401 if the token is missing or invalid.
    """
    # A token must be present and must be sent as a "Bearer" token.
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Send a valid Clerk token as 'Authorization: Bearer <token>'.",
        )

    token = authorization.split(" ", 1)[1].strip()

    # Refuse to accept anything if the backend isn't configured with the Clerk secret key.
    if not config.CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured with CLERK_SECRET_KEY.",
        )

    # Ask Clerk's servers to validate the token's signature and expiry.
    # The public signing key is fetched once and cached by the SDK.
    try:
        claims = verify_token(
            token,
            VerifyTokenOptions(secret_key=config.CLERK_SECRET_KEY),
        )
    except TokenVerificationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token.",
        )

    # The "sub" (subject) claim is the Clerk user ID for this merchant.
    merchant_id = claims.get("sub")
    if not merchant_id:
        raise HTTPException(
            status_code=401,
            detail="Token is valid but does not contain a user ID.",
        )

    return merchant_id


def get_optional_merchant_id(authorization: str = Header(None)) -> Optional[str]:
    """
    FastAPI dependency for routes that work BOTH signed-in and anonymous.

    - Valid Bearer token  -> returns the Clerk user ID (merchant is scoped).
    - No header at all     -> returns None (caller decides a default tenant).
    - Present but invalid  -> still raises 401 (never silently downgrades).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()

    if not config.CLERK_SECRET_KEY:
        raise HTTPException(
            status_code=500,
            detail="Server is not configured with CLERK_SECRET_KEY.",
        )

    try:
        claims = verify_token(
            token,
            VerifyTokenOptions(secret_key=config.CLERK_SECRET_KEY),
        )
    except TokenVerificationError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired session token.",
        )

    return claims.get("sub")