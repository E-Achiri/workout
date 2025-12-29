import os
import httpx
from typing import Optional
from functools import lru_cache
from jose import jwt, JWTError
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from database import get_cursor

# Cognito configuration from environment variables
COGNITO_REGION = os.getenv("COGNITO_REGION", "us-east-1")
COGNITO_USER_POOL_ID = os.getenv("COGNITO_USER_POOL_ID", "")
COGNITO_CLIENT_ID = os.getenv("COGNITO_CLIENT_ID", "")

# Construct the JWKS URL
COGNITO_ISSUER = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
COGNITO_JWKS_URL = f"{COGNITO_ISSUER}/.well-known/jwks.json"

security = HTTPBearer()


class TokenData(BaseModel):
    sub: str
    email: Optional[str] = None


class User(BaseModel):
    id: int
    cognito_sub: str
    email: Optional[str] = None


@lru_cache(maxsize=1)
def get_jwks():
    """Fetch and cache the JWKS from Cognito."""
    response = httpx.get(COGNITO_JWKS_URL)
    response.raise_for_status()
    return response.json()


def get_public_key(token: str):
    """Get the public key for verifying the token."""
    try:
        jwks = get_jwks()
        unverified_header = jwt.get_unverified_header(token)

        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header["kid"]:
                return key

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to get public key: {str(e)}",
        )


def verify_token(token: str) -> TokenData:
    """Verify and decode a Cognito JWT token."""
    try:
        public_key = get_public_key(token)

        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=COGNITO_ISSUER,
        )

        return TokenData(
            sub=payload.get("sub"),
            email=payload.get("email"),
        )
    except HTTPException:
        raise
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
        )


def get_or_create_user(token_data: TokenData) -> User:
    """Get existing user or create a new one based on Cognito sub."""
    with get_cursor() as cursor:
        # Try to find existing user
        cursor.execute(
            "SELECT id, cognito_sub, email FROM users WHERE cognito_sub = %s",
            (token_data.sub,)
        )
        row = cursor.fetchone()

        if row:
            # Update email if it changed
            if token_data.email and row["email"] != token_data.email:
                cursor.execute(
                    "UPDATE users SET email = %s WHERE id = %s",
                    (token_data.email, row["id"])
                )
            return User(**row)

        # Create new user
        cursor.execute(
            "INSERT INTO users (cognito_sub, email) VALUES (%s, %s) RETURNING id, cognito_sub, email",
            (token_data.sub, token_data.email)
        )
        row = cursor.fetchone()
        return User(**row)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency to get the current authenticated user."""
    token = credentials.credentials
    token_data = verify_token(token)
    return get_or_create_user(token_data)
