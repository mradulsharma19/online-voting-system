# create_admin.py - creates (or changes) the admin account. Run it once: python create_admin.py
# The password is typed at the prompt (it stays hidden) and is stored only as a hash.
import getpass
import os
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = os.environ.get('VOTING_DB') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')


def create_admin(username, password):
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT OR REPLACE INTO admins (username, password_hash) VALUES (?, ?)',
                 (username, generate_password_hash(password)))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    username = input('Admin username [admin]: ').strip() or 'admin'
    password = getpass.getpass('Admin password (typing is hidden, min 6 characters): ')
    again = getpass.getpass('Repeat password: ')

    if len(password) < 6:
        print('Password must be at least 6 characters. Nothing was saved.')
    elif password != again:
        print('Passwords do not match. Nothing was saved.')
    else:
        create_admin(username, password)
        print(f"Admin '{username}' saved. You can now log in at http://127.0.0.1:5000/admin/login")
