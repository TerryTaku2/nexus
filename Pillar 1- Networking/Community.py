from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Dict, List
import sqlite3

app = FastAPI()


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


async def deliver_offline_messages(websocket: WebSocket, user_id: int, db_path: str = "Database/Nexus.db"):
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

            conn = sqlite3.connect("Database/Nexus.db")
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