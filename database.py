# database.py - creates the SQLite database and the 3 tables (run this once)
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Table 1: voters (eligible roll numbers, their hashed password, and whether they voted)
cursor.execute('''
CREATE TABLE IF NOT EXISTS voters (
    roll_no TEXT PRIMARY KEY,
    password_hash TEXT,
    has_voted INTEGER DEFAULT 0
)
''')

# Table 2: candidates (name and running vote total)
cursor.execute('''
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    vote_count INTEGER DEFAULT 0
)
''')

# Table 3: election_settings (one row of switches, used more in Milestone 3)
cursor.execute('''
CREATE TABLE IF NOT EXISTS election_settings (
    id INTEGER PRIMARY KEY,
    registration_start TEXT,
    registration_end TEXT,
    voting_open INTEGER DEFAULT 0,
    results_visible INTEGER DEFAULT 0
)
''')

cursor.execute('SELECT COUNT(*) FROM election_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute("INSERT INTO election_settings (id, registration_start, registration_end, voting_open, results_visible) VALUES (1, '', '', 0, 0)")

conn.commit()
conn.close()
print("Database and tables created successfully.")
