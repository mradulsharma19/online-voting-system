# app.py - main Flask application (Milestone 2: registration, login, voting)
import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'change-this-to-any-random-text'   # needed so Flask can use session safely

# database file always sits next to app.py, whichever folder the terminal is in
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')


def get_db():
    return sqlite3.connect(DB_PATH)



# REGISTER: voter sets a password once (only if roll no. is eligible)

@app.route('/', methods=['GET', 'POST'])
def register_page():
    message = ''
    if request.method == 'POST':
        roll_no = request.form['roll_no'].strip()
        password = request.form['password']

        if roll_no == '' or password == '':
            message = 'Please fill both fields.'
        elif len(password) < 4:
            message = 'Password must be at least 4 characters.'
        else:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM voters WHERE roll_no = ?', (roll_no,))
            row = cursor.fetchone()

            if row is None:
                message = 'This roll number is not eligible to register.'
            elif row[0]:
                message = 'This roll number is already registered.'
            else:
                # store only the hashed (scrambled) password
                hashed = generate_password_hash(password)
                cursor.execute('UPDATE voters SET password_hash = ? WHERE roll_no = ?', (hashed, roll_no))
                conn.commit()
                conn.close()
                return render_template('message.html', title='Registration successful',
                                       text='You are registered. You can now log in and vote.',
                                       link='/login', link_text='Go to Login')
            conn.close()

    return render_template('register.html', message=message)



# LOGIN: check roll no. + password, then remember the voter in session

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    message = ''
    if request.method == 'POST':
        roll_no = request.form['roll_no'].strip()
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM voters WHERE roll_no = ?', (roll_no,))
        row = cursor.fetchone()
        conn.close()

        # same message for every failure, so outsiders cannot guess valid roll numbers
        if row is None or not row[0] or not check_password_hash(row[0], password):
            message = 'Invalid roll number or password.'
        else:
            session['roll_no'] = roll_no
            return redirect(url_for('vote_page'))

    return render_template('login.html', message=message)



# VOTE: only for logged-in voters, only once

@app.route('/vote', methods=['GET', 'POST'])
def vote_page():
    # not logged in -> back to login page
    if 'roll_no' not in session:
        return redirect(url_for('login_page'))

    roll_no = session['roll_no']
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT has_voted FROM voters WHERE roll_no = ?', (roll_no,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        session.clear()
        return redirect(url_for('login_page'))

    # duplicate vote check
    if row[0] == 1:
        conn.close()
        return render_template('message.html', title='Already voted',
                               text='You have already cast your vote. A voter can vote only once.',
                               link='/logout', link_text='Logout')

    if request.method == 'POST':
        candidate_id = request.form.get('candidate')
        if not candidate_id:
            cursor.execute('SELECT candidate_id, name FROM candidates')
            candidates = cursor.fetchall()
            conn.close()
            return render_template('vote.html', candidates=candidates, roll_no=roll_no,
                                   message='Please select a candidate first.')

        # voting algorithm: +1 to the candidate, mark this voter as voted
        cursor.execute('UPDATE candidates SET vote_count = vote_count + 1 WHERE candidate_id = ?', (candidate_id,))
        cursor.execute('UPDATE voters SET has_voted = 1 WHERE roll_no = ?', (roll_no,))
        conn.commit()
        conn.close()
        return render_template('message.html', title='Vote recorded',
                               text='Your vote has been recorded. Thank you for voting!',
                               link='/logout', link_text='Logout')

    cursor.execute('SELECT candidate_id, name FROM candidates')
    candidates = cursor.fetchall()
    conn.close()
    return render_template('vote.html', candidates=candidates, roll_no=roll_no, message='')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))



# ADMIN: read-only dashboard preview (controls are added in Milestone 3)

@app.route('/admin')
def admin_page():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT candidate_id, name, vote_count FROM candidates')
    candidates = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM voters')
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM voters WHERE password_hash IS NOT NULL AND password_hash != ''")
    registered = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM voters WHERE has_voted = 1')
    voted = cursor.fetchone()[0]
    conn.close()
    return render_template('admin.html', candidates=candidates, total=total,
                           registered=registered, voted=voted)


if __name__ == '__main__':
    app.run(debug=True)
