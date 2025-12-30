import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import init_db, get_cursor
from auth import get_current_user, User

app = FastAPI(title="Workout API")

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize the database on startup."""
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization skipped (may not be available): {e}")


class MessageCreate(BaseModel):
    message: str


class MessageResponse(BaseModel):
    id: int
    message: str
    created_at: str


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Workout API is running"}


@app.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "cognito_sub": current_user.cognito_sub,
    }


@app.post("/messages")
def create_message(
    body: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new message for the current user."""
    with get_cursor() as cursor:
        cursor.execute(
            "INSERT INTO messages (user_id, message) VALUES (%s, %s) RETURNING id, message, created_at",
            (current_user.id, body.message)
        )
        row = cursor.fetchone()

    return {
        "id": row["id"],
        "message": row["message"],
        "created_at": str(row["created_at"]),
    }


@app.get("/messages")
def get_messages(current_user: User = Depends(get_current_user)):
    """Get all messages for the current user."""
    with get_cursor() as cursor:
        cursor.execute(
            "SELECT id, message, created_at FROM messages WHERE user_id = %s ORDER BY created_at DESC",
            (current_user.id,)
        )
        rows = cursor.fetchall()

    return {
        "messages": [
            {
                "id": row["id"],
                "message": row["message"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]
    }


@app.delete("/messages/{message_id}")
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete a message by ID (only if owned by current user)."""
    with get_cursor() as cursor:
        cursor.execute(
            "DELETE FROM messages WHERE id = %s AND user_id = %s RETURNING id",
            (message_id, current_user.id)
        )
        row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"deleted": True, "id": message_id}
