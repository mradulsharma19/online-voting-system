# database.py - creates the database and tables (run once; safe to run again).
# Milestone 3: adds the admins table and the registration_open switch.
# If you already have a voting.db from Milestone 2, running this file upgrades it.
import os
import sqlite3

DB_PATH = os.environ.get('VOTING_DB') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Table 1: voters (eligible roll numbers, hashed password, voted or not)
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

# Table 3: election_settings (one row of on/off switches controlled by the admin)
# registration_start / registration_end are kept for the registration window we add later.
cursor.execute('''
CREATE TABLE IF NOT EXISTS election_settings (
    id INTEGER PRIMARY KEY,
    registration_start TEXT,
    registration_end TEXT,
    registration_open INTEGER DEFAULT 0,
    voting_open INTEGER DEFAULT 0,
    results_visible INTEGER DEFAULT 0
)
''')

# Table 4 (new in Milestone 3): admins (admin username + hashed password)
cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL
)
''')

# Upgrade path: a Milestone 2 database has no registration_open column yet
cursor.execute('PRAGMA table_info(election_settings)')
existing_columns = [row[1] for row in cursor.fetchall()]
if 'registration_open' not in existing_columns:
    cursor.execute('ALTER TABLE election_settings ADD COLUMN registration_open INTEGER DEFAULT 0')
    print("Upgraded election_settings: added registration_open column.")

# Make sure the single settings row exists
cursor.execute('SELECT COUNT(*) FROM election_settings')
if cursor.fetchone()[0] == 0:
    cursor.execute('''
    INSERT INTO election_settings (id, registration_start, registration_end, registration_open, voting_open, results_visible)
    VALUES (1, '', '', 0, 0, 0)
    ''')

conn.commit()
conn.close()
print("Database and tables are ready.")
