"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import base64
import binascii
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

session_secret = os.getenv("SESSION_SECRET", "development-secret-change-me").encode()
session_cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
session_max_age = 60 * 60 * 8

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

users = {}
admin_emails = {
    email.strip().lower()
    for email in os.getenv("ADMIN_EMAILS", "teacher@mergington.edu").split(",")
    if email.strip()
}


class UserCredentials(BaseModel):
    name: str
    email: str
    password: str


class LoginCredentials(BaseModel):
    email: str
    password: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def create_session(email: str) -> str:
    payload = json.dumps({"email": email, "expires": int(time.time()) + session_max_age}, separators=(",", ":")).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(session_secret, encoded_payload.encode(), hashlib.sha256).hexdigest()
    return f"{encoded_payload}.{signature}"


def get_session_email(request: Request) -> str | None:
    token = request.cookies.get("session")
    if not token or "." not in token:
        return None
    encoded_payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        session_secret, encoded_payload.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        padding = "=" * (-len(encoded_payload) % 4)
        session = json.loads(base64.urlsafe_b64decode(encoded_payload + padding))
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError):
        return None
    if not isinstance(session, dict) or session.get("expires", 0) < time.time():
        return None
    return session.get("email")


def set_session(response: Response, email: str) -> None:
    response.set_cookie(
        "session",
        create_session(email),
        max_age=session_max_age,
        httponly=True,
        secure=session_cookie_secure,
        samesite="lax",
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 600_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_password: str) -> bool:
    salt_hex, digest_hex = stored_password.split("$", 1)
    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), 600_000
    )
    return hmac.compare_digest(expected.hex(), digest_hex)


def public_user(user: dict) -> dict:
    return {
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }


def get_current_user(request: Request) -> dict:
    email = get_session_email(request)
    if not email or email not in users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return users[email]


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return user


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(credentials: UserCredentials, response: Response):
    email = normalize_email(credentials.email)
    if "@" not in email or not credentials.name.strip():
        raise HTTPException(status_code=400, detail="Name and a valid email are required")
    if len(credentials.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if email in users:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    users[email] = {
        "name": credentials.name.strip(),
        "email": email,
        "password_hash": hash_password(credentials.password),
        "role": "admin" if email in admin_emails else "student",
    }
    set_session(response, email)
    return public_user(users[email])


@app.post("/auth/login")
def login(credentials: LoginCredentials, response: Response):
    email = normalize_email(credentials.email)
    user = users.get(email)
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    set_session(response, email)
    return public_user(user)


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("session")
    return {"message": "Logged out"}


@app.get("/auth/me")
def current_user(user: dict = Depends(get_current_user)):
    return public_user(user)


@app.get("/admin/activities")
def get_admin_activities(user: dict = Depends(require_admin)):
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, user: dict = Depends(get_current_user)):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    email = user["email"]
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    requested_email: str | None = None,
    user: dict = Depends(get_current_user),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    email = user["email"]
    if user["role"] == "admin" and requested_email:
        email = normalize_email(requested_email)
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
