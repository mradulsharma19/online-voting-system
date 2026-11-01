# Online Voting System

A web-based voting system built with **Python, Flask and SQLite** as a college micro-project. An admin prepares the election and controls each phase. Eligible voters register once, log in while voting is open and vote exactly once. The vote stays secret: the database stores only a total for each candidate, never who voted for whom.

## Features

- **Admin module:** admin login, add and remove candidates, load and remove roll numbers, and three phase switches (registration, voting, results)
- **Election phases:** registration, voting and results never overlap. The system refuses any change that would break the order.
- **Eligible list only:** a student can register only if the admin has loaded their roll number
- **One-time registration:** each roll number registers once and sets its own password
- **Hashed passwords:** voter and admin passwords are stored only as hashes
- **One vote per voter:** a conditional update on `has_voted` blocks double votes, even from two browser sessions
- **Secret ballot:** no table links a voter to a candidate
- **Results page:** totals only, shown after voting is closed and the admin publishes them
- **Home page:** one page with buttons for Register, Voter Login, Results and Admin Login, each with a live Open/Closed tag

## Tech Stack

| Part | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, Jinja templates |
| Password security | Werkzeug password hashing |

## How an Election Works

1. **Admin** logs in, loads the eligible roll numbers and adds at least 2 candidates.
2. **Admin** opens registration. Each student registers once at `/register`.
3. **Admin** closes registration and starts voting. Each student logs in at `/login` and votes once.
4. **Admin** stops voting and shows the results. Anyone can open `/results`.

### Rules the System Enforces

| Action | Rule |
|---|---|
| Open registration | Not allowed while voting is open |
| Start voting | Not allowed while registration is open or results are visible, and needs at least 2 candidates |
| Show results | Not allowed while voting is open |
| Add or remove a candidate | Not allowed while voting is open or after any vote exists |
| Load roll numbers | Not allowed while voting is open |
| Remove a roll number | Not allowed while voting is open or results are visible, and never for a voter who has already voted |

## Pages

| Route | Description |
|---|---|
| `/` | Home page with a button for every part of the system |
| `/register` | Voter registration (only while registration is open) |
| `/login` | Voter login (only while voting is open) |
| `/vote` | Candidate list and vote (logged-in voters only) |
| `/results` | Candidate totals (after voting closes and the admin publishes) |
| `/admin/login` | Admin login |
| `/admin` | Admin dashboard (protected) |

## Database

Four tables in `voting.db`:

| Table | Columns |
|---|---|
| `voters` | `roll_no` (primary key), `password_hash`, `has_voted` |
| `candidates` | `candidate_id` (primary key), `name`, `vote_count` |
| `election_settings` | `registration_open`, `voting_open`, `results_visible`, plus `registration_start` and `registration_end` (kept for a planned registration window) |
| `admins` | `username` (primary key), `password_hash` |

There is intentionally no table linking a voter to a candidate.

## Getting Started

### Requirements

- Python 3.9 or newer
- pip

### Run it

Open a terminal **inside the project folder** and run:

```
pip install flask
python database.py
python create_admin.py
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

- `database.py` creates the database and tables. It is safe to run again, and it upgrades an older database.
- `create_admin.py` asks for an admin username and password. Typing the password is hidden.
- `app.py` starts the server.

### Optional: load sample data

```
python sample_voters.py
```

Adds the sample roll numbers `0101AI26001` to `0101AI26005` and three sample candidates. You can also load roll numbers and candidates from the admin dashboard.

### Helper scripts

| Script | What it does |
|---|---|
| `show_results.py` | Prints the switches, vote counts and voter status in the terminal |
| `reset_demo.py` | Resets registrations, votes and switches (the admin account is kept) |

### Automatic tests

```
python run_tests.py
```

Runs 86 end-to-end checks on a temporary database, so your real data is never touched.

## Project Structure

```
app.py             Flask app: voter routes, admin routes, results
database.py        Creates and upgrades the database
create_admin.py    Creates the admin account
sample_voters.py   Adds sample roll numbers and candidates (optional)
show_results.py    Prints switches, counts and voter status
reset_demo.py      Resets the demo
run_tests.py       Automatic tests
requirements.txt   Python dependencies
templates/         HTML pages
static/style.css   Shared stylesheet
```

## Security Notes

- Voter and admin passwords are stored only as hashes
- SQL uses placeholders, which protects against SQL injection
- Wrong roll number and wrong password give the same error message
- Admin pages are protected, and the admin session is separate from the voter session
- Candidate names are escaped by the templates
- Set the `SECRET_KEY` environment variable for real use. In PowerShell: `$env:SECRET_KEY="your-long-random-text"`
- Never upload `voting.db` to GitHub

## Milestones

| # | Milestone | Deadline | Status |
|---|---|---|---|
| 1 | Requirement Analysis and Architectural Design | 2 Oct 2026 | Completed |
| 2 | Core Module Implementation and Prototyping | 17 Oct 2026 | Completed |
| 3 | Integration and Intermediate Evaluation (admin module, election phases, results page, home page, automatic tests) | 1 Nov 2026 | Completed |
| 4 | Comprehensive Testing and Optimization | 16 Nov 2026 | Next |
| 5 | Deployment, Final Documentation and Viva Preparation | 1 Dec 2026 | Planned |

### Planned for Milestone 4

- Security testing (SQL injection, XSS, CSRF) and a short audit report
- Load testing and query optimization
- Limit on repeated wrong password attempts
- User manual for voters and admin

## Known Limitations

- No CSRF protection yet
- No limit on repeated wrong password attempts
- Registration uses an open/close switch. A start and end date-time window is planned.
- A local fallback secret key exists for development
- No password reset for voters
- SQLite suits small elections only

## Future Scope

- Registration window with start and end date-time
- OTP-based verification during registration
- Live turnout and charts on the admin dashboard
- Admin audit log (actions only, never who voted for whom)
- Online hosting for a live demo

## Author

**Mradul Sharma**
B.Tech Artificial Intelligence, Madhav Institute of Technology and Science, Gwalior

Under the guidance of **Dr. Rishabh Deo Pandey**, Assistant Professor
