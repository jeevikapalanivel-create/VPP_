import sqlite3

# Connect to SQLite DB
conn = sqlite3.connect("earthmover.db")
cursor = conn.cursor()

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS machines (
    machine_id TEXT PRIMARY KEY,
    machine_name TEXT,
    type TEXT,
    purchase_date DATE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS daily_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    machine_id TEXT,
    hours_worked REAL,
    rate_per_hour REAL,
    operator TEXT,
    income REAL,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    machine_id TEXT,
    expense_type TEXT,
    amount REAL,
    remarks TEXT,
    FOREIGN KEY (machine_id) REFERENCES machines(machine_id)
)
""")

conn.commit()
conn.close()
print("✅ Database and tables created successfully.")
