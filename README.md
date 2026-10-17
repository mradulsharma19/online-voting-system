# Online Voting System

A simple web-based voting system built with **Python, Flask and SQLite** as a college micro-project. An eligible voter registers once with their roll number, logs in, and can cast exactly one vote. It is designed for small elections such as class or club voting.

## Features

- **Eligible list only:** a student can register only if their roll number is already on the list loaded by the admin
- **One-time registration:** every roll number can register just once
- **Hashed passwords:** passwords are never stored as plain text
- **Login with sessions:** the voting page cannot be opened without logging in
- **One vote per voter:** a `has_voted` flag blocks any second vote
- **Secret ballot:** the database never stores which voter chose which candidate, only a total count per candidate
- **Admin dashboard (preview):** shows eligible voters, registered voters, votes cast and candidate totals

## Tech Stack

| Part | Technology |
|---|---|
| Backend | Python, Flask |
| Database | SQLite |
| Frontend | HTML, CSS, Jinja templates |
| Password security | Werkzeug password hashing |

## How It Works

1. The admin loads the list of eligible roll numbers and the candidates into the database.
2. A student opens the register page and sets a password. The roll number must be on the eligible list and must not be registered already.
3. The student logs in with the roll number and password. Flask remembers the login in a session.
4. On the voting page the student picks one candidate. The candidate's vote count goes up by one and the voter is marked as `has_voted`.
5. Any later attempt to vote is blocked.

## Pages

| Route | Page | Description |
|---|---|---|
| `/` | Register | Roll number and new password |
| `/login` | Login | Roll number and password |
| `/vote` | Vote | Candidate list, one choice, only for logged-in voters |
| `/logout` | Logout | Ends the session |
| `/admin` | Admin dashboard | Read-only summary (controls come in Milestone 3) |

## Database

Three tables are used in `voting.db`:

**voters**

| Column | Type | Description |
|---|---|---|
| `roll_no` | TEXT (primary key) | Unique roll number |
| `password_hash` | TEXT | Hashed password, empty until the student registers |
| `has_voted` | INTEGER | 0 = not voted, 1 = voted |

**candidates**

| Column | Type | Description |
|---|---|---|
| `candidate_id` | INTEGER (primary key) | Auto-incremented id |
| `name` | TEXT | Candidate name |
| `vote_count` | INTEGER | Total votes received |

**election_settings**

| Column | Type | Description |
|---|---|---|
| `registration_start`, `registration_end` | TEXT | Registration window |
| `voting_open` | INTEGER | Voting on/off switch |
| `results_visible` | INTEGER | Results on/off switch |

There is intentionally no table that links a voter to the candidate they chose, so the vote stays secret.

## Getting Started

### Prerequisites

- Python 3.9 or newer
- pip

### Installation and run

```
pip install flask
python database.py
python sample_voters.py
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

- `database.py` creates the database and the tables (run once)
- `sample_voters.py` adds sample roll numbers (`BTAI26O1001` to `BTAI26O1005`) and
  five sample candidates (run once)

To use real roll numbers, edit the lists at the top of `sample_voters.py`, delete `voting.db`, and run `database.py` and `sample_voters.py` again.

### Try it out

| Step | Expected result |
|---|---|
| Register with roll no `9999` | "This roll number is not eligible to register." |
| Register with `BTAI26O1001` and a password | Registration successful |
| Register with `BTAI26O1001` again | "This roll number is already registered." |
| Log in with a wrong password | "Invalid roll number or password." |
| Log in with the correct details | Voting page with the candidate list |
| Submit a vote | "Your vote has been recorded." |
| Open `/vote` again | "You have already cast your vote." |
| Open `/admin` | Summary and candidate totals |

To see the totals in the terminal, run `python show_results.py`. To repeat the demo from scratch, run `python reset_demo.py`.

## Project Structure

```
app.py             Flask app (register, login, vote, logout, admin preview)
database.py        Creates the database and the three tables
sample_voters.py   Adds sample voters and candidates
show_results.py    Prints vote counts and voter status in the terminal
reset_demo.py      Resets registrations and votes for a fresh demo
requirements.txt   Python dependencies
templates/         HTML pages (register, login, vote, message, admin)
static/style.css   Shared stylesheet
```

## Security Notes

- Passwords are stored only as hashes (Werkzeug), never as plain text.
- SQL queries use placeholders (`?`), which protects against SQL injection.
- The login page shows the same error for a wrong roll number and a wrong password, so valid roll numbers cannot be guessed.
- The voting page checks the session before showing anything.
- The `has_voted` check runs both before the candidates are shown and when the vote is submitted.

## Milestones

| # | Milestone | Deadline | Status |
|---|---|---|---|
| 1 | Requirement Analysis and Architectural Design (SRS, architecture diagram, database schema, UI wireframes) | 2 Oct 2026 | Completed |
| 2 | Core Module Implementation and Prototyping (database handlers, registration, login, voting logic, basic templates) | 17 Oct 2026 | Completed |
| 3 | Integration and Intermediate Evaluation (admin module, voting and results switches, results page, code review, usability test) | 1 Nov 2026 | Planned |
| 4 | Comprehensive Testing and Optimization (security testing, edge cases, query optimization, user manual) | 16 Nov 2026 | Planned |
| 5 | Deployment, Final Documentation and Viva Preparation | 1 Dec 2026 | Planned |

### Done in Milestone 2

- Database with `voters`, `candidates` and `election_settings` tables
- Registration for eligible roll numbers with hashed passwords
- Login with session handling
- Voting with a duplicate-vote check
- Read-only admin dashboard preview

### Planned for Milestone 3

- Admin login and admin controls
- Add and remove candidates from the browser
- Voting on/off and results on/off switches
- Registration time window set by the admin
- Results page showing only candidate totals, visible only after voting is closed

## Known Limitations

- The `/admin` page has no login yet (added in Milestone 3).
- The `voting_open` and `results_visible` switches exist in the database but are not enforced in the code yet.
- Sample voters and candidates are loaded with `sample_voters.py` instead of the browser.
- The Flask `secret_key` is written in the code; for real hosting it should come from an environment variable.
- There is no CSRF protection yet.
- SQLite is suitable for small elections, not for very large ones.

## Future Scope

- Automatic start and stop of registration and voting by date and time
- OTP-based verification during registration
- Real-time vote count updates with charts on the admin dashboard
- Admin audit log (actions only, never who voted for whom)
- Hosting online so voting can be done from any device

## Author

**Mradul Sharma**
B.Tech Artificial Intelligence, Madhav Institute of Technology and Science, Gwalior

Under the guidance of **Dr. Rishabh Deo Pandey**, Assistant Professor
