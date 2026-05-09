from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
from datetime import datetime, timezone

app = FastAPI(title="Social Features API")

DB_PATH = "../Database/Nexus.db"

class PostCreate(BaseModel):
    author_id: int
    content: str

class PostResponse(BaseModel):
    id: int
    author_id: int
    content: str
    time_posted: str

class UpdateCreate(BaseModel):
    user_id: int
    update_text: str

class UpdateResponse(BaseModel):
    id: int
    user_id: int
    update_text: str
    time_posted: str

class SME(BaseModel):
    id: int
    name: str
    category: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]

class FollowRequest(BaseModel):
    follower_id: int
    target_id: int

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_local_timestamp() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")

def format_timestamp_to_local(timestamp_str: str) -> str:
    if not timestamp_str:
        return timestamp_str
    try:
        if "T" in timestamp_str or "+" in timestamp_str or timestamp_str.endswith("Z"):
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")).astimezone()
        else:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            dt = dt.replace(tzinfo=timezone.utc).astimezone()
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp_str

@app.post("/posts", response_model=PostResponse)
async def create_post(post: PostCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        local_time = get_local_timestamp()
        cursor.execute(
            "INSERT INTO Posts (author_id, content, time_posted) VALUES (?, ?, ?)",
            (post.author_id, post.content, local_time)
        )
        post_id = cursor.lastrowid
        conn.commit()

        result = cursor.execute(
            "SELECT id, author_id, content, time_posted FROM Posts WHERE id = ?",
            (post_id,)
        ).fetchone()

        return {
            "id": result["id"],
            "author_id": result["author_id"],
            "content": result["content"],
            "time_posted": format_timestamp_to_local(result["time_posted"])
        }
    finally:
        conn.close()

@app.get("/posts", response_model=List[PostResponse])
async def get_posts():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, author_id, content, time_posted FROM Posts ORDER BY time_posted DESC"
        ).fetchall()

        return [
            {
                "id": row["id"],
                "author_id": row["author_id"],
                "content": row["content"],
                "time_posted": format_timestamp_to_local(row["time_posted"])
            }
            for row in results
        ]
    finally:
        conn.close()

@app.get("/posts/{author_id}", response_model=List[PostResponse])
async def get_user_posts(author_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, author_id, content, time_posted FROM Posts WHERE author_id = ? ORDER BY time_posted DESC",
            (author_id,)
        ).fetchall()

        return [
            {
                "id": row["id"],
                "author_id": row["author_id"],
                "content": row["content"],
                "time_posted": format_timestamp_to_local(row["time_posted"])
            }
            for row in results
        ]
    finally:
        conn.close()

@app.post("/updates", response_model=UpdateResponse)
async def create_update(update: UpdateCreate):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        local_time = get_local_timestamp()
        cursor.execute(
            "INSERT INTO Updates (user_id, update_text, time_posted) VALUES (?, ?, ?)",
            (update.user_id, update.update_text, local_time)
        )
        update_id = cursor.lastrowid
        conn.commit()

        result = cursor.execute(
            "SELECT id, user_id, update_text, time_posted FROM Updates WHERE id = ?",
            (update_id,)
        ).fetchone()

        return {
            "id": result["id"],
            "user_id": result["user_id"],
            "update_text": result["update_text"],
            "time_posted": format_timestamp_to_local(result["time_posted"])
        }
    finally:
        conn.close()

@app.get("/updates", response_model=List[UpdateResponse])
async def get_updates():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, user_id, update_text, time_posted FROM Updates ORDER BY time_posted DESC"
        ).fetchall()

        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "update_text": row["update_text"],
                "time_posted": format_timestamp_to_local(row["time_posted"])
            }
            for row in results
        ]
    finally:
        conn.close()

@app.get("/updates/{user_id}", response_model=List[UpdateResponse])
async def get_user_updates(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, user_id, update_text, time_posted FROM Updates WHERE user_id = ? ORDER BY time_posted DESC",
            (user_id,)
        ).fetchall()

        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "update_text": row["update_text"],
                "time_posted": format_timestamp_to_local(row["time_posted"])
            }
            for row in results
        ]
    finally:
        conn.close()

@app.get("/smes", response_model=List[SME])
async def get_smes():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, name, category, latitude, longitude FROM SMEs"
        ).fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "latitude": row["latitude"],
                "longitude": row["longitude"]
            }
            for row in results
        ]
    finally:
        conn.close()

@app.get("/smes/{category}", response_model=List[SME])
async def get_smes_by_category(category: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT id, name, category, latitude, longitude FROM SMEs WHERE category = ?",
            (category,)
        ).fetchall()

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row["category"],
                "latitude": row["latitude"],
                "longitude": row["longitude"]
            }
            for row in results
        ]
    finally:
        conn.close()

@app.post("/follow")
async def follow_user(follow: FollowRequest):
    if follow.follower_id == follow.target_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if already following
        existing = cursor.execute(
            "SELECT id FROM Followers WHERE user_id = ? AND target_id = ?",
            (follow.follower_id, follow.target_id)
        ).fetchone()

        if existing:
            raise HTTPException(status_code=400, detail="Already following")

        cursor.execute(
            "INSERT INTO Followers (user_id, target_id) VALUES (?, ?)",
            (follow.follower_id, follow.target_id)
        )
        conn.commit()

        return {"message": "Following successfully"}
    finally:
        conn.close()

@app.delete("/follow/{follower_id}/{target_id}")
async def unfollow_user(follower_id: int, target_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM Followers WHERE user_id = ? AND target_id = ?",
            (follower_id, target_id)
        )
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not following")

        return {"message": "Unfollowed successfully"}
    finally:
        conn.close()

@app.get("/followers/{user_id}")
async def get_followers(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT user_id, target_id FROM Followers WHERE target_id = ?",
            (user_id,)
        ).fetchall()

        return [{"follower_id": row["user_id"], "target_id": row["target_id"]} for row in results]
    finally:
        conn.close()

@app.get("/following/{user_id}")
async def get_following(user_id: int):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        results = cursor.execute(
            "SELECT user_id, target_id FROM Followers WHERE user_id = ?",
            (user_id,)
        ).fetchall()

        return [{"follower_id": row["user_id"], "target_id": row["target_id"]} for row in results]
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
