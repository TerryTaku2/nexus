from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import sqlite3
import os
from datetime import datetime

app = FastAPI(title="Community Networking and Social Features API")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Database", "Nexus.db"))


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)

    async def broadcast(self, message: dict, user_ids: List[int]):
        for user_id in user_ids:
            if user_id in self.active_connections:
                websocket = self.active_connections[user_id]
                await websocket.send_json(message)


manager = ConnectionManager()


# ======================== Social Features Models ========================

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


# ======================== Helper Functions ========================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_local_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def format_timestamp_to_local(timestamp_str: str) -> str:
    return timestamp_str


async def deliver_offline_messages(websocket: WebSocket, user_id: int, db_path: str = DB_PATH):
    """Deliver missed messages to user and update their last_seen timestamp."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Get user's last_seen timestamp
        user_record = conn.execute(
            "SELECT last_seen FROM Users WHERE ID = ?",
            (user_id,)
        ).fetchone()

        if not user_record:
            conn.close()
            return

        last_seen = user_record["last_seen"]

        # Get missed direct messages
        missed_direct = conn.execute("""
            SELECT DISTINCT 
                m.message_id,
                m.message,
                m.sender,
                m.sent_to_chat,
                m.time_sent,
                u.business_name as sender_name
            FROM Messages m
            JOIN Users u ON m.sender = u.ID
            WHERE m.time_sent > ?
                AND m.sent_to_chat IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM Chats c
                    WHERE c.ID = m.sent_to_chat
                    AND (c.user_1 = ? OR c.user_2 = ?)
                    AND (c.user_1 = m.sender OR c.user_2 = m.sender)
                )
            ORDER BY m.time_sent ASC
        """, (last_seen, user_id, user_id))

        # Get missed group messages
        missed_group = conn.execute("""
            SELECT DISTINCT 
                m.message_id,
                m.message,
                m.sender,
                m.sent_to_group,
                m.time_sent,
                u.business_name as sender_name,
                g.name as group_name
            FROM Messages m
            JOIN Users u ON m.sender = u.ID
            JOIN Groups g ON m.sent_to_group = g.ID
            JOIN Group_Members gm ON gm.group_id = m.sent_to_group
            WHERE m.time_sent > ?
                AND gm.user_id = ?
                AND m.sender != ?
            ORDER BY m.time_sent ASC
        """, (last_seen, user_id, user_id))

        # Send missed direct messages
        for message in missed_direct:
            await websocket.send_json({
                "type": "chat",
                "message": message["message"],
                "sender_id": message["sender"],
                "sender_name": message["sender_name"],
                "sent_to": message["sent_to_chat"],
                "time_sent": message["time_sent"],
                "is_offline": True
            })

        # Send missed group messages
        for message in missed_group:
            await websocket.send_json({
                "type": "group",
                "message": message["message"],
                "sender_id": message["sender"],
                "sender_name": message["sender_name"],
                "group_id": message["sent_to_group"],
                "group_name": message["group_name"],
                "time_sent": message["time_sent"],
                "is_offline": True
            })

        # Update last_seen to current timestamp
        conn.execute(
            "UPDATE Users SET last_seen = CURRENT_TIMESTAMP WHERE ID = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()

    except Exception as e:
        print(f"Error during offline message delivery for user {user_id}: {e}")
        try:
            conn.close()
        except:
            pass


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)

    # Deliver any missed messages
    await deliver_offline_messages(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()

            message = data.get("message")
            sent_to = data.get("sent_to")
            chat_type = data.get("type")

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row

            if chat_type == "chat":
                # Save message to database
                cursor = conn.execute("""
                    INSERT INTO Messages (message, sender, sent_to_chat, sent_to_group, read)
                    VALUES (?, ?, ?, NULL, ?)
                """, (message, user_id, sent_to, "no"))

                # Get the timestamp of the inserted message
                message_id = cursor.lastrowid
                time_sent = conn.execute(
                    "SELECT time_sent FROM Messages WHERE message_id = ?",
                    (message_id,)
                ).fetchone()["time_sent"]

                # Get sender's business name
                sender = conn.execute(
                    "SELECT business_name FROM Users WHERE ID = ?",
                    (user_id,)
                ).fetchone()

                conn.commit()
                conn.close()

                # Send enriched message to single user (matching offline format)
                enriched_message = {
                    "type": "chat",
                    "message": message,
                    "sender_id": user_id,
                    "sender_name": sender["business_name"],
                    "sent_to": sent_to,
                    "time_sent": time_sent,
                    "is_offline": False
                }
                await manager.send_personal_message(enriched_message, sent_to)

            elif chat_type == "group":
                # Get sender's business name
                sender = conn.execute(
                    "SELECT business_name FROM Users WHERE ID = ?",
                    (user_id,)
                ).fetchone()

                # Get group name
                group = conn.execute(
                    "SELECT name FROM Groups WHERE ID = ?",
                    (sent_to,)
                ).fetchone()

                # Save message to database
                cursor = conn.execute("""
                    INSERT INTO Messages (message, sender, sent_to_chat, sent_to_group, read)
                    VALUES (?, ?, NULL, ?, ?)
                """, (message, user_id, sent_to, "N/A"))

                # Get the timestamp of the inserted message
                message_id = cursor.lastrowid
                time_sent = conn.execute(
                    "SELECT time_sent FROM Messages WHERE message_id = ?",
                    (message_id,)
                ).fetchone()["time_sent"]

                conn.commit()

                # Get group members
                members = conn.execute(
                    "SELECT user_id FROM Group_Members WHERE group_id = ?",
                    (sent_to,)
                ).fetchall()

                conn.close()

                # Prepare enriched message matching offline format
                enriched_message = {
                    "type": "group",
                    "message": message,
                    "sender_id": user_id,
                    "sender_name": sender["business_name"],
                    "group_id": sent_to,
                    "group_name": group["name"],
                    "time_sent": time_sent,
                    "is_offline": False
                }

                member_ids = [member["user_id"] for member in members]
                await manager.broadcast(enriched_message, member_ids)

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ======================== HTTP Endpoints for REST API ========================

@app.get("/chats/{user_id}")
async def get_user_chats(user_id: int):
    """Get all chats for a user (both direct and group)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Get direct chats
        direct_chats = conn.execute("""
            SELECT 
                c.ID as chat_id,
                CASE 
                    WHEN c.user_1 = ? THEN c.user_2 
                    ELSE c.user_1 
                END as other_user_id,
                u.business_name as other_user_name,
                u.last_seen as other_user_last_seen,
                (
                    SELECT message FROM Messages 
                    WHERE sent_to_chat = c.ID 
                    ORDER BY time_sent DESC LIMIT 1
                ) as last_message,
                (
                    SELECT time_sent FROM Messages 
                    WHERE sent_to_chat = c.ID 
                    ORDER BY time_sent DESC LIMIT 1
                ) as last_message_time
            FROM Chats c
            JOIN Users u ON (
                CASE 
                    WHEN c.user_1 = ? THEN c.user_2 = u.ID
                    ELSE c.user_1 = u.ID
                END
            )
            WHERE c.user_1 = ? OR c.user_2 = ?
        """, (user_id, user_id, user_id, user_id)).fetchall()

        # Get group chats
        group_chats = conn.execute("""
            SELECT 
                g.ID as group_id,
                g.name as group_name,
                g.date_created,
                gm.user_id as member_id,
                u.business_name as member_name,
                (
                    SELECT message FROM Messages 
                    WHERE sent_to_group = g.ID 
                    ORDER BY time_sent DESC LIMIT 1
                ) as last_message,
                (
                    SELECT time_sent FROM Messages 
                    WHERE sent_to_group = g.ID 
                    ORDER BY time_sent DESC LIMIT 1
                ) as last_message_time
            FROM Groups g
            JOIN Group_Members gm ON g.ID = gm.group_id
            JOIN Users u ON gm.user_id = u.ID
            WHERE gm.user_id = ?
        """, (user_id,)).fetchall()

        return {
            "direct_chats": [dict(chat) for chat in direct_chats],
            "group_chats": [dict(chat) for chat in group_chats]
        }
    finally:
        conn.close()


@app.get("/messages/chat/{chat_id}")
async def get_chat_messages(chat_id: int, limit: int = 50):
    """Get messages from a specific chat."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        messages = conn.execute("""
            SELECT 
                m.message_id,
                m.message,
                m.sender,
                m.time_sent,
                m.read,
                u.business_name as sender_name
            FROM Messages m
            JOIN Users u ON m.sender = u.ID
            WHERE m.sent_to_chat = ?
            ORDER BY m.time_sent DESC
            LIMIT ?
        """, (chat_id, limit)).fetchall()

        return [dict(msg) for msg in messages]
    finally:
        conn.close()


@app.get("/messages/group/{group_id}")
async def get_group_messages(group_id: int, limit: int = 50):
    """Get messages from a specific group."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        messages = conn.execute("""
            SELECT 
                m.message_id,
                m.message,
                m.sender,
                m.time_sent,
                m.read,
                u.business_name as sender_name,
                g.name as group_name
            FROM Messages m
            JOIN Users u ON m.sender = u.ID
            JOIN Groups g ON m.sent_to_group = g.ID
            WHERE m.sent_to_group = ?
            ORDER BY m.time_sent DESC
            LIMIT ?
        """, (group_id, limit)).fetchall()

        return [dict(msg) for msg in messages]
    finally:
        conn.close()


@app.post("/groups")
async def create_group(name: str, admin_id: int, member_ids: List[int]):
    """Create a new group with members."""
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()

        # Create group
        cursor.execute(
            "INSERT INTO Groups (name, admin) VALUES (?, ?)",
            (name, admin_id)
        )
        group_id = cursor.lastrowid

        # Add admin as member
        cursor.execute(
            "INSERT INTO Group_Members (user_id, group_id) VALUES (?, ?)",
            (admin_id, group_id)
        )

        # Add other members
        for member_id in member_ids:
            if member_id != admin_id:  # Avoid duplicate admin
                cursor.execute(
                    "INSERT INTO Group_Members (user_id, group_id) VALUES (?, ?)",
                    (member_id, group_id)
                )

        conn.commit()
        return {"group_id": group_id, "message": "Group created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()


@app.get("/groups/{group_id}/members")
async def get_group_members(group_id: int):
    """Get all members of a group."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        members = conn.execute("""
            SELECT 
                u.ID,
                u.business_name,
                u.owner_name,
                u.email
            FROM Group_Members gm
            JOIN Users u ON gm.user_id = u.ID
            WHERE gm.group_id = ?
        """, (group_id,)).fetchall()

        return [dict(member) for member in members]
    finally:
        conn.close()


# ======================== Social Features Endpoints ========================

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