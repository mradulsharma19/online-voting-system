# app.py - main Flask application (Milestone 3: voter side + admin module + election phases)
import os
import re
import sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# secret key signs the session cookie. For real hosting set the SECRET_KEY environment variable.
app.secret_key = os.environ.get('SECRET_KEY', 'dev-only-secret-change-me')

# database file sits next to app.py (VOTING_DB can override it, used by run_tests.py)
DB_PATH = os.environ.get('VOTING_DB') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'voting.db')


def get_db():
    return sqlite3.connect(DB_PATH)


def get_settings(cursor):
    """Read the three admin switches from the single row in election_settings."""
    cursor.execute('SELECT registration_open, voting_open, results_visible FROM election_settings WHERE id = 1')
    row = cursor.fetchone()
    if row is None:
        return {'registration_open': 0, 'voting_open': 0, 'results_visible': 0}
    return {'registration_open': row[0], 'voting_open': row[1], 'results_visible': row[2]}


def read_settings():
    conn = get_db()
    settings = get_settings(conn.cursor())
    conn.close()
    return settings


def admin_required(view):
    """Route protection: only a logged-in admin may open the page, everyone else goes to the admin login."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return view(*args, **kwargs)
    return wrapped


# =====================================================================
# VOTER SIDE
# =====================================================================

# ---------- HOME PAGE (one page with a button for every part of the system) ----------
@app.route('/')
def home_page():
    return render_template('home.html', settings=read_settings())


# ---------- REGISTER (only while the admin has registration open) ----------
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    settings = read_settings()
    if not settings['registration_open']:
        return render_template('register.html', message='Registration is closed right now.', registration_open=False)

    message = ''
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip().upper()
        password = request.form.get('password', '')

        if roll_no == '' or password == '':
            message = 'Please fill both fields.'
        elif len(password) < 4:
            message = 'Password must be at least 4 characters.'
        else:
            conn = get_db()
            cursor = conn.cursor()
            # roll numbers are compared in capital letters, so 0101ai26001 and 0101AI26001 are the same
            cursor.execute('SELECT roll_no, password_hash FROM voters WHERE UPPER(roll_no) = ?', (roll_no,))
            row = cursor.fetchone()

            if row is None:
                message = 'This roll number is not eligible to register.'
            elif row[1]:
                message = 'This roll number is already registered.'
            else:
                hashed = generate_password_hash(password)
                # the "password is still empty" condition makes the update safe even if two requests arrive together
                cursor.execute(
                    "UPDATE voters SET password_hash = ? WHERE roll_no = ? AND (password_hash IS NULL OR password_hash = '')",
                    (hashed, row[0]))
                if cursor.rowcount == 1:
                    conn.commit()
                    conn.close()
                    return render_template('message.html', title='Registration successful',
                                           text='You are registered. You can log in once the admin opens voting.',
                                           link='/login', link_text='Go to Login')
                message = 'This roll number is already registered.'
            conn.close()

    return render_template('register.html', message=message, registration_open=True)


# ---------- LOGIN (only while the admin has voting open) ----------
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    settings = read_settings()
    if not settings['voting_open']:
        return render_template('login.html', message='Voting is not open right now.', voting_open=False)

    message = ''
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip().upper()
        password = request.form.get('password', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT roll_no, password_hash FROM voters WHERE UPPER(roll_no) = ?', (roll_no,))
        row = cursor.fetchone()
        conn.close()

        # one message for every failure, so outsiders cannot find out which roll numbers exist
        if row is None or not row[1] or not check_password_hash(row[1], password):
            message = 'Invalid roll number or password.'
        else:
            session['roll_no'] = row[0]
            return redirect(url_for('vote_page'))

    return render_template('login.html', message=message, voting_open=True)


# ---------- VOTE (logged-in voters only, voting must be open, one vote each) ----------
def render_vote_page(conn, roll_no, message):
    cursor = conn.cursor()
    cursor.execute('SELECT candidate_id, name FROM candidates ORDER BY candidate_id')
    candidates = cursor.fetchall()
    conn.close()
    return render_template('vote.html', candidates=candidates, roll_no=roll_no, message=message)


@app.route('/vote', methods=['GET', 'POST'])
def vote_page():
    if 'roll_no' not in session:
        return redirect(url_for('login_page'))

    roll_no = session['roll_no']

    # the admin may have closed voting after this voter logged in
    if not read_settings()['voting_open']:
        return render_template('message.html', title='Voting closed',
                               text='Voting is not open right now.', link='/logout', link_text='Logout')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT has_voted FROM voters WHERE roll_no = ?', (roll_no,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        session.clear()
        return redirect(url_for('login_page'))

    if row[0] == 1:
        conn.close()
        return render_template('message.html', title='Already voted',
                               text='You have already cast your vote. A voter can vote only once.',
                               link='/logout', link_text='Logout')

    if request.method == 'POST':
        # the form value must be a whole number that belongs to a real candidate
        try:
            candidate_id = int(request.form.get('candidate', ''))
        except ValueError:
            return render_vote_page(conn, roll_no, 'Please select a candidate first.')

        cursor.execute('SELECT 1 FROM candidates WHERE candidate_id = ?', (candidate_id,))
        if cursor.fetchone() is None:
            return render_vote_page(conn, roll_no, 'Invalid candidate. Please choose from the list.')

        # step 1: mark the voter as voted, but only if they have not voted yet (this blocks double votes)
        cursor.execute('UPDATE voters SET has_voted = 1 WHERE roll_no = ? AND has_voted = 0', (roll_no,))
        if cursor.rowcount != 1:
            conn.close()
            return render_template('message.html', title='Already voted',
                                   text='You have already cast your vote. A voter can vote only once.',
                                   link='/logout', link_text='Logout')

        # step 2: add one vote to the candidate. Both steps are saved together by one commit().
        cursor.execute('UPDATE candidates SET vote_count = vote_count + 1 WHERE candidate_id = ?', (candidate_id,))
        conn.commit()
        conn.close()
        return render_template('message.html', title='Vote recorded',
                               text='Your vote has been recorded. Thank you for voting!',
                               link='/logout', link_text='Logout')

    return render_vote_page(conn, roll_no, '')


@app.route('/logout')
def logout():
    session.pop('roll_no', None)
    return redirect(url_for('login_page'))


# ---------- RESULTS (public page, but only after voting is closed and the admin publishes) ----------
@app.route('/results')
def results_page():
    conn = get_db()
    cursor = conn.cursor()
    settings = get_settings(cursor)

    if not settings['results_visible'] or settings['voting_open']:
        conn.close()
        return render_template('message.html', title='Results not available',
                               text='Results are shown only after voting is closed and the admin publishes them.',
                               link='/login', link_text='Back to Login')

    cursor.execute('SELECT name, vote_count FROM candidates ORDER BY vote_count DESC, name ASC')
    candidates = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM voters')
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM voters WHERE password_hash IS NOT NULL AND password_hash != ''")
    registered = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM voters WHERE has_voted = 1')
    voted = cursor.fetchone()[0]
    conn.close()

    top = candidates[0][1] if candidates else 0
    return render_template('results.html', candidates=candidates, top=top,
                           total=total, registered=registered, voted=voted)


# =====================================================================
# ADMIN SIDE
# =====================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('is_admin'):
        return redirect(url_for('admin_page'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM admins WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()

        if row is None or not check_password_hash(row[0], password):
            message = 'Invalid admin username or password.'
        else:
            session['is_admin'] = True
            session['admin_name'] = username
            return redirect(url_for('admin_page'))

    return render_template('admin_login.html', message=message)


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_page():
    conn = get_db()
    cursor = conn.cursor()
    settings = get_settings(cursor)

    cursor.execute('SELECT candidate_id, name, vote_count FROM candidates ORDER BY candidate_id')
    candidates = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) FROM voters')
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM voters WHERE password_hash IS NOT NULL AND password_hash != ''")
    registered = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM voters WHERE has_voted = 1')
    voted = cursor.fetchone()[0]
    # the admin sees only registered yes/no and voted yes/no, never which candidate a voter chose
    cursor.execute("SELECT roll_no, (password_hash IS NOT NULL AND password_hash != ''), has_voted "
                   "FROM voters ORDER BY roll_no")
    voters = cursor.fetchall()
    conn.close()

    return render_template('admin.html', admin_name=session.get('admin_name'), settings=settings,
                           candidates=candidates, total=total, registered=registered, voted=voted,
                           voters=voters,
                           candidates_locked=bool(settings['voting_open'] or voted > 0),
                           voters_locked=bool(settings['voting_open'] or settings['results_visible']),
                           show_votes=not settings['voting_open'])


# the three on/off switches: URL name -> (database column, text when switched on, text when switched off)
SWITCHES = {
    'registration': ('registration_open', 'Registration is now open.', 'Registration is now closed.'),
    'voting': ('voting_open', 'Voting is now open.', 'Voting is now closed.'),
    'results': ('results_visible', 'Results are now visible.', 'Results are now hidden.'),
}


@app.route('/admin/toggle/<name>', methods=['POST'])
@admin_required
def admin_toggle(name):
    if name not in SWITCHES:
        abort(404)
    column, text_on, text_off = SWITCHES[name]

    conn = get_db()
    cursor = conn.cursor()
    settings = get_settings(cursor)
    new_value = 0 if settings[column] else 1

    # safety rules, so the phases never overlap
    error = None
    if new_value == 1:
        if name == 'registration' and settings['voting_open']:
            error = 'Stop voting before opening registration.'
        elif name == 'voting' and settings['registration_open']:
            error = 'Close registration before starting voting.'
        elif name == 'voting' and settings['results_visible']:
            error = 'Hide the results before starting voting.'
        elif name == 'voting':
            cursor.execute('SELECT COUNT(*) FROM candidates')
            if cursor.fetchone()[0] < 2:
                error = 'Add at least 2 candidates before starting voting.'
        elif name == 'results' and settings['voting_open']:
            error = 'Stop voting before showing results.'

    if error:
        flash(error, 'error')
    else:
        # the column name comes from our own SWITCHES dictionary, never from the user
        cursor.execute(f'UPDATE election_settings SET {column} = ? WHERE id = 1', (new_value,))
        conn.commit()
        flash(text_on if new_value else text_off, 'success')
    conn.close()
    return redirect(url_for('admin_page'))


def candidates_are_locked(cursor):
    """Candidates may only be changed before voting starts and before any vote exists."""
    settings = get_settings(cursor)
    cursor.execute('SELECT COUNT(*) FROM voters WHERE has_voted = 1')
    return bool(settings['voting_open'] or cursor.fetchone()[0] > 0)


LOCKED_MESSAGE = 'Candidates cannot be changed while voting is open or after votes have been cast.'


@app.route('/admin/add_candidate', methods=['POST'])
@admin_required
def admin_add_candidate():
    name = request.form.get('candidate_name', '').strip()
    conn = get_db()
    cursor = conn.cursor()

    if candidates_are_locked(cursor):
        flash(LOCKED_MESSAGE, 'error')
    elif len(name) < 1 or len(name) > 60:
        flash('Candidate name must be 1 to 60 characters.', 'error')
    else:
        cursor.execute('SELECT 1 FROM candidates WHERE UPPER(name) = ?', (name.upper(),))
        if cursor.fetchone():
            flash('A candidate with this name already exists.', 'error')
        else:
            cursor.execute('INSERT INTO candidates (name) VALUES (?)', (name,))
            conn.commit()
            flash('Candidate added.', 'success')
    conn.close()
    return redirect(url_for('admin_page'))


@app.route('/admin/remove_candidate/<int:candidate_id>', methods=['POST'])
@admin_required
def admin_remove_candidate(candidate_id):
    conn = get_db()
    cursor = conn.cursor()

    if candidates_are_locked(cursor):
        flash(LOCKED_MESSAGE, 'error')
    else:
        cursor.execute('DELETE FROM candidates WHERE candidate_id = ?', (candidate_id,))
        if cursor.rowcount == 1:
            conn.commit()
            flash('Candidate removed.', 'success')
        else:
            flash('Candidate not found.', 'error')
    conn.close()
    return redirect(url_for('admin_page'))


@app.route('/admin/load_voters', methods=['POST'])
@admin_required
def admin_load_voters():
    raw = request.form.get('roll_numbers', '')
    conn = get_db()
    cursor = conn.cursor()

    if read_settings()['voting_open']:
        flash('Roll numbers cannot be loaded while voting is open.', 'error')
    else:
        # roll numbers can be separated by spaces, commas, semicolons or new lines
        items = [x.strip().upper() for x in re.split(r'[\s,;]+', raw) if x.strip()]
        if not items:
            flash('Please paste at least one roll number.', 'error')
        else:
            valid_format = re.compile(r'^[A-Z0-9_-]{3,20}$')
            added = existing = invalid = 0
            for item in items:
                if not valid_format.match(item):
                    invalid += 1
                    continue
                cursor.execute('SELECT 1 FROM voters WHERE UPPER(roll_no) = ?', (item,))
                if cursor.fetchone():
                    existing += 1
                    continue
                cursor.execute('INSERT INTO voters (roll_no, password_hash, has_voted) VALUES (?, NULL, 0)', (item,))
                added += 1
            conn.commit()
            flash(f'Added {added} roll number(s). Already present: {existing}. Invalid: {invalid}.',
                  'success' if added else 'error')
    conn.close()
    return redirect(url_for('admin_page'))


@app.route('/admin/remove_voter', methods=['POST'])
@admin_required
def admin_remove_voter():
    roll_no = request.form.get('roll_no', '').strip()
    conn = get_db()
    cursor = conn.cursor()
    settings = get_settings(cursor)

    # safety rules: not during voting, not while results are public, never for a voter who has voted
    if settings['voting_open']:
        flash('Roll numbers cannot be removed while voting is open.', 'error')
    elif settings['results_visible']:
        flash('Hide the results before removing roll numbers.', 'error')
    else:
        cursor.execute('SELECT has_voted FROM voters WHERE roll_no = ?', (roll_no,))
        row = cursor.fetchone()
        if row is None:
            flash('Roll number not found.', 'error')
        elif row[0] == 1:
            flash('This voter has already voted, so the roll number cannot be removed.', 'error')
        else:
            # "AND has_voted = 0" keeps the delete safe even if a vote arrives at the same moment
            cursor.execute('DELETE FROM voters WHERE roll_no = ? AND has_voted = 0', (roll_no,))
            if cursor.rowcount == 1:
                conn.commit()
                flash(f'Roll number {roll_no} removed.', 'success')
            else:
                flash('This voter has already voted, so the roll number cannot be removed.', 'error')
    conn.close()
    return redirect(url_for('admin_page'))


if __name__ == '__main__':
    app.run(debug=True)
