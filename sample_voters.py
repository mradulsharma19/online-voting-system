# sample_voters.py - adds sample eligible roll numbers and candidates (run once after database.py)
# Admin controls are built in Milestone 3, so for now sample data is loaded from here.
# You can edit the two lists below and put real roll numbers / names.
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')

ELIGIBLE_ROLL_NUMBERS = ['BTAI26O1001', 'BTAI26O1002', 'BTAI26O1003', 'BTAI26O1004', 'BTAI26O1076']
CANDIDATE_NAMES = ['Candidate A', 'Candidate B', 'Candidate C']

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for roll in ELIGIBLE_ROLL_NUMBERS:
    cursor.execute('INSERT OR IGNORE INTO voters (roll_no, password_hash, has_voted) VALUES (?, NULL, 0)', (roll,))

cursor.execute('SELECT COUNT(*) FROM candidates')
if cursor.fetchone()[0] == 0:
    for name in CANDIDATE_NAMES:
        cursor.execute('INSERT INTO candidates (name) VALUES (?)', (name,))

conn.commit()
conn.close()
print("Sample voters and candidates added.")
