# reset_demo.py - resets the demo: voters unregistered, votes 0, all switches off. Admin account is kept.
import os
import sqlite3

DB_PATH = os.environ.get('VOTING_DB') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('UPDATE voters SET password_hash = NULL, has_voted = 0')
cursor.execute('UPDATE candidates SET vote_count = 0')
cursor.execute('UPDATE election_settings SET registration_open = 0, voting_open = 0, results_visible = 0 WHERE id = 1')
conn.commit()
conn.close()
print("Demo reset. Voters are unregistered, all votes are 0 and all switches are off.")
