
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'app.db')

def add_column():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(alarms)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'device_ids' in columns:
            print("Column 'device_ids' already exists in 'alarms' table.")
        else:
            print("Adding 'device_ids' column to 'alarms' table...")
            cursor.execute("ALTER TABLE alarms ADD COLUMN device_ids TEXT")
            conn.commit()
            print("Column added successfully.")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
