from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime
import hashlib
import secrets
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Database", "Nexus.db"))

app = FastAPI(title="NeXus Login API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"pbkdf2:{salt}:{key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2:"):
        try:
            _, salt, stored_key = stored.split(":", 2)
            key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
            return key.hex() == stored_key
        except Exception:
            return False
    # Legacy plain-text fallback — migrated to hash on next successful login
    return password == stored


def safe_user(row) -> dict:
    d = dict(row)
    d.pop("password", None)
    return d


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    city: str = Field(..., min_length=2, max_length=50)
    sector: str = Field(..., min_length=2, max_length=50)
    registration_number: Optional[str] = None
    employees: Optional[str] = None
    years_active: Optional[str] = None
    email: EmailStr
    password: str = Field(..., min_length=6)


@app.post("/api/auth/login")
async def login(data: LoginRequest):
    conn = get_db()
    try:
        user = conn.execute("SELECT * FROM Users WHERE email=?", (data.email,)).fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(data.password, user["password"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Migrate plain-text password to hashed on successful login
        if not user["password"].startswith("pbkdf2:"):
            conn.execute(
                "UPDATE Users SET password=? WHERE ID=?",
                (hash_password(data.password), user["ID"])
            )
            conn.commit()

        return {
            "success": True,
            "user": safe_user(user),
            "redirect": "../dashboard/dashboard.html"
        }
    finally:
        conn.close()


@app.post("/api/auth/register")
async def register(data: SignupRequest):
    conn = get_db()
    try:
        existing = conn.execute("SELECT ID FROM Users WHERE email=?", (data.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")

        conn.execute("""
            INSERT INTO Users (
                business_name, owner_name, phone, city, sector,
                registration_number, employees, years_active, email, password, last_seen
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            data.business_name, data.owner_name, data.phone,
            data.city, data.sector, data.registration_number,
            data.employees, data.years_active, data.email,
            hash_password(data.password), datetime.now()
        ))
        conn.commit()

        user = conn.execute("SELECT * FROM Users WHERE email=?", (data.email,)).fetchone()
        return {
            "success": True,
            "user": safe_user(user),
            "redirect": "../dashboard/dashboard.html"
        }
    except HTTPException:
        raise
    finally:
        conn.close()
