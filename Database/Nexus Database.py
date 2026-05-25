# Nexus Database.py
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

    # ============ TOOLKIT TABLES ============

    # Inventory Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            current_stock REAL DEFAULT 0,
            reorder_level REAL DEFAULT 0,
            cost_price REAL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Loans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lender_name TEXT NOT NULL,
            loan_type TEXT NOT NULL CHECK (loan_type IN ('business', 'personal', 'microfinance', 'p2p')),
            principal REAL NOT NULL,
            interest_rate REAL NOT NULL,
            term_months INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'defaulted')),
            amount_paid REAL DEFAULT 0,
            next_due_date TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Loan Payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Loan_Payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_date TEXT NOT NULL,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (loan_id) REFERENCES Loans(id) ON DELETE CASCADE
        )
    """)

    # Sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            unit_cost REAL NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('Rent', 'Utilities', 'Salaries', 'Transport', 'Marketing', 'Inventory', 'Other')),
            description TEXT,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Capital Contributions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Capital (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Bookkeeping Entries table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Bookkeeping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('sale', 'purchase', 'expense')),
            description TEXT,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT,
            supplier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Notification Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Notification_Settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            notification_email TEXT,
            inventory_alerts INTEGER DEFAULT 1,
            loan_alerts INTEGER DEFAULT 1,
            loan_days_before INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(ID)
        )
    """)

    # Create indexes for toolkit tables
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_user ON Inventory(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loans_user ON Loans(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_loan_payments_loan ON Loan_Payments(loan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_user ON Sales(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON Sales(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_user ON Expenses(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_expenses_date ON Expenses(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_capital_user ON Capital(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookkeeping_user ON Bookkeeping(user_id)")

    conn.commit()
    conn.close()

    print(f"Database '{db_path}' created successfully with all tables.")


if __name__ == "__main__":
    create_database()