# show_results.py - prints the current vote counts and voter status (useful for screenshots/proof)
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n--- Candidates and vote counts ---")
for cid, name, count in cursor.execute('SELECT candidate_id, name, vote_count FROM candidates'):
    print(f"{cid}. {name}: {count} vote(s)")

print("\n--- Voters (password is stored as a hash, never plain text) ---")
for roll, pw, voted in cursor.execute('SELECT roll_no, password_hash, has_voted FROM voters'):
    registered = 'registered' if pw else 'not registered'
    print(f"{roll}: {registered}, has_voted = {voted}")
conn.close()
