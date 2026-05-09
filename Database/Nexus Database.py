# schema.py
import sqlite3



def create_database(db_path="Nexus.db"):
    """Create the SQLite database with all required tables."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Create Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            sector TEXT NOT NULL,
            registration_number TEXT,
            employees INTEGER,
            years_active INTEGER,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Groups table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Groups (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            admin INTEGER NOT NULL,
            FOREIGN KEY (admin) REFERENCES Users(ID)
        )
    """)

    # Create Chats table (for single chats)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Chats (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            user_1 INTEGER NOT NULL,
            user_2 INTEGER NOT NULL,
            FOREIGN KEY (user_1) REFERENCES Users(ID),
            FOREIGN KEY (user_2) REFERENCES Users(ID),
            UNIQUE(user_1, user_2)
        )
    """)

    # Create Group_Members table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Group_Members (
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            PRIMARY KEY (user_id, group_id),
            FOREIGN KEY (user_id) REFERENCES Users(ID),
            FOREIGN KEY (group_id) REFERENCES Groups(ID)
        )
    """)

    # Create Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            sender INTEGER NOT NULL,
            sent_to_chat INTEGER,
            sent_to_group INTEGER,
            time_sent TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            read TEXT NOT NULL CHECK (read IN ('yes', 'no', 'N/A')),
            FOREIGN KEY (sender) REFERENCES Users(ID),
            FOREIGN KEY (sent_to_chat) REFERENCES Chats(ID),
            FOREIGN KEY (sent_to_group) REFERENCES Groups(ID),
            CHECK (
                (sent_to_chat IS NOT NULL AND sent_to_group IS NULL) OR
                (sent_to_chat IS NULL AND sent_to_group IS NOT NULL)
            )
        )
    """)

    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_sender 
        ON Messages(sender)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_chat 
        ON Messages(sent_to_chat, time_sent)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_group 
        ON Messages(sent_to_group, time_sent)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chats_users 
        ON Chats(user_1, user_2)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_group_members_group 
        ON Group_Members(group_id)
    """)

    # Create Posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            author_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            time_posted TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES Users(ID)
        )
    """)

    # Create Updates table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            update_text TEXT NOT NULL,
            time_posted TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Create SMEs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SMEs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            latitude REAL,
            longitude REAL
        )
    """)

    # Create Followers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            target_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(ID),
            FOREIGN KEY (target_id) REFERENCES Users(ID),
            UNIQUE(user_id, target_id)
        )
    """)

    conn.commit()
    conn.close()

    print(f"Database '{db_path}' created successfully with all tables.")


if __name__ == "__main__":
    create_database()