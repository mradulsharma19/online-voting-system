# reset_demo.py - resets all demo data so you can run the demo / take screenshots again
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute('UPDATE voters SET password_hash = NULL, has_voted = 0')
cursor.execute('UPDATE candidates SET vote_count = 0')
conn.commit()
conn.close()
print("Demo data reset. All voters are unregistered again and all votes are 0.")
