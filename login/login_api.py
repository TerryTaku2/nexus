from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import sqlite3
from datetime import datetime

app = FastAPI(title="Login API")


class SignupRequest(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=15)
    city: str = Field(..., min_length=2, max_length=50)
    sector: str = Field(..., min_length=2, max_length=50)
    registration_number: Optional[str] = None
    employees: Optional[int] = None
    years_active: Optional[int] = None
    email: EmailStr
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@app.post("/signup")
async def sign_in(login_data: LoginRequest):
    conn = sqlite3.connect("chat_app.db")
    conn.row_factory = sqlite3.Row

    try:
        user = conn.execute(
            "SELECT * FROM Users WHERE email = ?",
            (login_data.email,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if user["password"] != login_data.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")


        conn.commit()

        return {"message": "Login successful", "user": dict(user)}

    finally:
        conn.close()


@app.post("/create_account")
async def create_account(user_data: SignupRequest):
    conn = sqlite3.connect("chat_app.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        existing = cursor.execute(
            "SELECT ID FROM Users WHERE email = ?",
            (user_data.email,)
        ).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        last_seen = datetime.now()

        cursor.execute("""
            INSERT INTO Users (
                business_name, owner_name, phone, city, sector,
                registration_number, employees, years_active, email, password, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_data.business_name, user_data.owner_name, user_data.phone,
            user_data.city, user_data.sector, user_data.registration_number,
            user_data.employees, user_data.years_active, user_data.email,
            user_data.password, last_seen
        ))

        conn.commit()

        user = conn.execute(
            "SELECT * FROM Users WHERE ID = ?", (cursor.lastrowid,)
        ).fetchone()

        return {"message": "Account created successfully", "user": dict(user)}

    except HTTPException:
        raise
    finally:
        conn.close()