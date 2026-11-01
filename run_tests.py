# run_tests.py - automatic end-to-end tests. Run: python run_tests.py
# It uses a temporary database, so your real voting.db is never touched.
import os
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp()
os.environ['VOTING_DB'] = os.path.join(TMP, 'test_voting.db')
sys.path.insert(0, HERE)

subprocess.run([sys.executable, os.path.join(HERE, 'database.py')], check=True, env=os.environ,
               stdout=subprocess.DEVNULL)

from app import app                      # noqa: E402  (imported after the test database is set)
from create_admin import create_admin    # noqa: E402

create_admin('admin', 'admin-pass-123')

results = []


def check(name, condition):
    results.append((name, bool(condition)))
    print(('PASS  ' if condition else 'FAIL  ') + name)


def page(response):
    return response.get_data(as_text=True)


def db_query(sql, params=()):
    conn = sqlite3.connect(os.environ['VOTING_DB'])
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return rows


anon = app.test_client()
admin = app.test_client()


def admin_post(url, data=None):
    return page(admin.post(url, data=data or {}, follow_redirects=True))


def voter_login(client, roll, password):
    return client.post('/login', data={'roll_no': roll, 'password': password})


print('\n--- Admin access ---')
check('admin page redirects to admin login when not logged in', anon.get('/admin').status_code == 302)
check('admin action is blocked when not logged in', anon.post('/admin/toggle/voting').status_code == 302)
check('wrong admin password is rejected',
      'Invalid admin username or password' in page(anon.post('/admin/login', data={'username': 'admin', 'password': 'bad'})))
check('correct admin login opens the dashboard',
      'ADMIN DASHBOARD' in page(admin.post('/admin/login', data={'username': 'admin', 'password': 'admin-pass-123'}, follow_redirects=True)))
check('admin password is stored as a hash', db_query('SELECT password_hash FROM admins')[0][0] != 'admin-pass-123')
check('unknown switch name returns 404', admin.post('/admin/toggle/evil').status_code == 404)

print('\n--- Home page ---')
home = page(anon.get('/'))
check('home page opens with all four buttons',
      anon.get('/').status_code == 200 and all(t in home for t in ['href="/register"', 'href="/login"', 'href="/results"', 'href="/admin/login"']))
check('home page shows every phase as closed at the start', 'tag closed' in home and 'tag open' not in home)
check('the old register address (/) no longer accepts POST', anon.post('/', data={}).status_code == 405)

print('\n--- Loading roll numbers and candidates ---')
text = admin_post('/admin/load_voters', {'roll_numbers': '0101AI26001 0101ai26002, 0101AI26003\n0101AI26004;bad!id'})
check('roll numbers loaded (4 added, 1 invalid)', 'Added 4' in text and 'Invalid: 1' in text)
text = admin_post('/admin/load_voters', {'roll_numbers': '0101AI26001 0101AI26002'})
check('loading the same roll numbers again adds nothing', 'Added 0' in text and 'Already present: 2' in text)
check('roll numbers are stored in capital letters', db_query("SELECT COUNT(*) FROM voters WHERE roll_no = '0101AI26002'")[0][0] == 1)
check('empty roll number box is rejected', 'at least one roll number' in admin_post('/admin/load_voters', {'roll_numbers': '  '}))
check('an extra roll number can be loaded', 'Added 1' in admin_post('/admin/load_voters', {'roll_numbers': '0101AI26005'}))
check('a roll number can be removed before voting',
      'Roll number 0101AI26005 removed.' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26005'}))
check('the removed roll number is really gone',
      db_query("SELECT COUNT(*) FROM voters WHERE roll_no='0101AI26005'")[0][0] == 0)
check('removing a roll number that does not exist is handled',
      'Roll number not found.' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26777'}))
check('removing a roll number needs admin login',
      anon.post('/admin/remove_voter', data={'roll_no': '0101AI26004'}).status_code == 302)

check('candidate A added', 'Candidate added.' in admin_post('/admin/add_candidate', {'candidate_name': 'Candidate A'}))
check('duplicate candidate name rejected (any letter case)',
      'already exists' in admin_post('/admin/add_candidate', {'candidate_name': 'candidate a'}))
check('empty candidate name rejected', '1 to 60' in admin_post('/admin/add_candidate', {'candidate_name': '   '}))
check('voting cannot start with fewer than 2 candidates',
      'at least 2 candidates' in admin_post('/admin/toggle/voting'))
admin_post('/admin/add_candidate', {'candidate_name': 'Candidate B'})
admin_post('/admin/add_candidate', {'candidate_name': 'Candidate C'})
text = admin_post('/admin/add_candidate', {'candidate_name': '<script>alert(1)</script>'})
check('candidate names are escaped in HTML (no script injection)',
      '&lt;script&gt;' in text and '<script>alert(1)</script>' not in text)
xss_id = db_query("SELECT candidate_id FROM candidates WHERE name LIKE '<script>%'")[0][0]
check('candidate can be removed before voting', 'Candidate removed.' in admin_post(f'/admin/remove_candidate/{xss_id}'))
check('removing a missing candidate is handled', 'Candidate not found.' in admin_post('/admin/remove_candidate/9999'))

ids = {n: i for i, n in db_query('SELECT candidate_id, name FROM candidates')}
check('three candidates exist', len(ids) == 3)

print('\n--- Registration phase ---')
v1, v2, v3 = app.test_client(), app.test_client(), app.test_client()
check('register page says closed while registration is off',
      'Registration is closed' in page(v1.get('/register')))
check('register POST is blocked while registration is off',
      'Registration is closed' in page(v1.post('/register', data={'roll_no': '0101AI26001', 'password': 'pass1'})))
check('registration opens', 'Registration is now open.' in admin_post('/admin/toggle/registration'))
check('home page shows registration as open', 'tag open' in page(anon.get('/')))
check('voting cannot start while registration is open',
      'Close registration before starting voting.' in admin_post('/admin/toggle/voting'))
check('non-eligible roll number rejected', 'not eligible' in page(v1.post('/register', data={'roll_no': '9999', 'password': 'pass1'})))
check('short password rejected', 'at least 4' in page(v1.post('/register', data={'roll_no': '0101AI26001', 'password': 'ab'})))
check('eligible roll number registers', 'Registration successful' in page(v1.post('/register', data={'roll_no': '0101AI26001', 'password': 'pass1'})))
check('same roll number cannot register twice', 'already registered' in page(v1.post('/register', data={'roll_no': '0101AI26001', 'password': 'other'})))
check('lowercase roll number registers (case-insensitive)',
      'Registration successful' in page(v2.post('/register', data={'roll_no': '0101ai26002', 'password': 'pass2'})))
check('passwords are stored as hashes',
      db_query("SELECT password_hash FROM voters WHERE roll_no='0101AI26001'")[0][0] not in ('pass1', None, ''))
check('login is blocked during registration (voting not open)',
      'Voting is not open' in page(voter_login(v1, '0101AI26001', 'pass1')))
check('registration closes', 'Registration is now closed.' in admin_post('/admin/toggle/registration'))

print('\n--- Voting phase ---')
check('results switch can be turned on while voting is closed',
      'Results are now visible.' in admin_post('/admin/toggle/results'))
check('voting cannot start while results are visible', 'Hide the results' in admin_post('/admin/toggle/voting'))
admin_post('/admin/toggle/results')
check('voting starts', 'Voting is now open.' in admin_post('/admin/toggle/voting'))
check('registration cannot open while voting is open',
      'Stop voting before opening registration.' in admin_post('/admin/toggle/registration'))
check('results cannot be shown while voting is open',
      'Stop voting before showing results.' in admin_post('/admin/toggle/results'))
check('/results page is blocked while voting is open', 'Results not available' in page(anon.get('/results')))
check('candidates cannot be added while voting is open',
      'cannot be changed' in admin_post('/admin/add_candidate', {'candidate_name': 'Late One'}))
check('roll numbers cannot be loaded while voting is open',
      'cannot be loaded while voting is open' in admin_post('/admin/load_voters', {'roll_numbers': '0101AI26099'}))
check('roll numbers cannot be removed while voting is open',
      'cannot be removed while voting is open' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26004'}))

check('vote page redirects to login when not logged in', anon.get('/vote').status_code == 302)
check('wrong password rejected', 'Invalid roll number or password' in page(voter_login(v1, '0101AI26001', 'wrong')))
check('unregistered roll number cannot log in',
      'Invalid roll number or password' in page(voter_login(v3, '0101AI26003', 'anything')))
r = voter_login(v1, '0101AI26001', 'pass1')
check('correct login redirects to the vote page', r.status_code == 302 and '/vote' in r.headers['Location'])
check('vote page lists candidates', all(n in page(v1.get('/vote')) for n in ['Candidate A', 'Candidate B', 'Candidate C']))
check('voting without a choice is rejected', 'select a candidate' in page(v1.post('/vote', data={})))
check('fake candidate id is rejected', 'Invalid candidate' in page(v1.post('/vote', data={'candidate': '999'})))
check('text instead of a number is rejected', 'select a candidate' in page(v1.post('/vote', data={'candidate': 'abc'})))
check('a rejected vote does NOT use up the voter\'s vote',
      db_query("SELECT has_voted FROM voters WHERE roll_no='0101AI26001'")[0][0] == 0)
check('valid vote is recorded',
      'vote has been recorded' in page(v1.post('/vote', data={'candidate': str(ids['Candidate B'])})))
check('candidate B has exactly 1 vote', db_query('SELECT vote_count FROM candidates WHERE name=?', ('Candidate B',))[0][0] == 1)
check('second vote on the page is blocked', 'already cast your vote' in page(v1.get('/vote')))
check('second vote by POST is blocked', 'already cast your vote' in page(v1.post('/vote', data={'candidate': str(ids['Candidate A'])})))
v1b = app.test_client()
voter_login(v1b, '0101AI26001', 'pass1')
check('second browser session cannot vote again',
      'already cast your vote' in page(v1b.post('/vote', data={'candidate': str(ids['Candidate A'])})))
check('totals unchanged after blocked attempts',
      db_query('SELECT SUM(vote_count) FROM candidates')[0][0] == 1)

voter_login(v2, '0101ai26002', 'pass2')
check('second voter (lowercase login) votes for A',
      'vote has been recorded' in page(v2.post('/vote', data={'candidate': str(ids['Candidate A'])})))
check('voter session cannot open the admin page', v1.get('/admin').status_code == 302)

text = page(admin.get('/admin'))
check('admin does not see vote counts while voting is open', 'Vote counts are hidden while voting is open' in text)
check('candidates are locked once voting is open', 'Candidates are locked' in text)

print('\n--- Closing and results ---')
check('voting stops', 'Voting is now closed.' in admin_post('/admin/toggle/voting'))
check('a voter who has voted cannot be removed',
      'already voted' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26001'}))
check('the voter who voted is still in the database',
      db_query("SELECT COUNT(*) FROM voters WHERE roll_no='0101AI26001'")[0][0] == 1)
check('a voter who has not voted can be removed after voting closes',
      'Roll number 0101AI26004 removed.' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26004'}))
check('logged-in voter cannot vote after the admin closes voting',
      'Voting is not open' in page(v2.get('/vote')))
check('login is blocked after voting is closed', 'Voting is not open' in page(voter_login(app.test_client(), '0101AI26001', 'pass1')))
check('candidates stay locked after votes were cast',
      'cannot be changed' in admin_post('/admin/add_candidate', {'candidate_name': 'Late Two'}))
check('results page still hidden until the admin publishes', 'Results not available' in page(anon.get('/results')))
check('results published', 'Results are now visible.' in admin_post('/admin/toggle/results'))
check('roll numbers cannot be removed while results are visible',
      'Hide the results before removing' in admin_post('/admin/remove_voter', {'roll_no': '0101AI26003'}))
res = page(anon.get('/results'))
check('results page shows candidate totals', 'Candidate A' in res and 'Candidate B' in res and 'Votes cast: 2 of 2' in res)
check('results page never shows roll numbers', '0101AI26001' not in res and '0101AI26002' not in res)
check('voting cannot restart while results are visible', 'Hide the results' in admin_post('/admin/toggle/voting'))
check('results hidden again', 'Results are now hidden.' in admin_post('/admin/toggle/results'))
check('results page blocked after hiding', 'Results not available' in page(anon.get('/results')))
check('admin logout works', admin.get('/admin/logout').status_code == 302 and admin.get('/admin').status_code == 302)

print('\n--- Upgrade from a Milestone 2 database ---')
old_db = os.path.join(TMP, 'old_m2.db')
conn = sqlite3.connect(old_db)
conn.executescript('''
CREATE TABLE voters (roll_no TEXT PRIMARY KEY, password_hash TEXT, has_voted INTEGER DEFAULT 0);
CREATE TABLE candidates (candidate_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, vote_count INTEGER DEFAULT 0);
CREATE TABLE election_settings (id INTEGER PRIMARY KEY, registration_start TEXT, registration_end TEXT,
                                voting_open INTEGER DEFAULT 0, results_visible INTEGER DEFAULT 0);
INSERT INTO election_settings VALUES (1, '', '', 0, 0);
INSERT INTO voters VALUES ('0101AI26001', 'x', 1);
''')
conn.commit()
conn.close()
env = dict(os.environ, VOTING_DB=old_db)
subprocess.run([sys.executable, os.path.join(HERE, 'database.py')], check=True, env=env, stdout=subprocess.DEVNULL)
conn = sqlite3.connect(old_db)
cols = [r[1] for r in conn.execute('PRAGMA table_info(election_settings)')]
kept = conn.execute("SELECT COUNT(*) FROM voters WHERE roll_no='0101AI26001'").fetchone()[0]
admins_ok = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='admins'").fetchone()[0]
conn.close()
check('old database gets the registration_open column', 'registration_open' in cols)
check('old data is kept after the upgrade', kept == 1)
check('admins table is created in the old database', admins_ok == 1)

passed = sum(1 for _, ok in results if ok)
print(f'\n{passed} of {len(results)} checks passed.')
print('ALL PASSED' if passed == len(results) else 'SOME FAILED')
sys.exit(0 if passed == len(results) else 1)
