# Railway Ticket Reservation — Web Edition

A web rebuild of the original Turbo C++ console "Train Reservation" program.
Same five core features, now running as a proper website.

- **Frontend:** plain HTML, CSS, and JavaScript (no framework, no build step)
- **Backend:** Python (Flask) REST API
- **Database:** SQLite (replaces the original's `Train1.dat` / `Ticket1.dat` binary files)

## How the original maps to this version

| Original console menu option        | Web equivalent                          |
|---------------------------------------|------------------------------------------|
| 1. Train Details                      | "Train Details" panel — live seat counts |
| 2. Update Train Details (password)    | "Update Train Details" panel — password-checked form |
| 3. Reserving a Ticket                 | "Reserve a Ticket" panel — confirms or waitlists |
| 4. Cancelling a Ticket                | "Cancel a Ticket" panel |
| 5. Display the Present Ticket Status  | "Check Ticket Status" panel |
| 6. Exit                               | not applicable to a website |

Two small, deliberate improvements over the original:
- The staff password on "Update Train Details" is actually checked (the
  original program asked for it but never validated it).
- Cancelling a confirmed ticket now automatically promotes the oldest
  waitlisted passenger in the same class, instead of just leaving a gap.

## Running it locally

```bash
cd train-reservation
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The SQLite database file (`train_reservation.db`) is created automatically
on first run, along with three sample trains so the site isn't empty.

## Project structure

```
train-reservation/
├── app.py                 Flask app & API routes
├── database.py             SQLite schema + all queries
├── requirements.txt
├── templates/
│   └── index.html          Single-page app shell
└── static/
    ├── css/style.css       Departure-board / ticket-stub styling
    └── js/app.js            Navigation + API calls + rendering
```

## API reference

| Method | Endpoint             | Purpose                              |
|--------|-----------------------|---------------------------------------|
| GET    | `/api/classes`        | List the five travel classes          |
| GET    | `/api/trains`          | List all trains                      |
| GET    | `/api/trains/<no>`    | One train + live seat availability    |
| POST   | `/api/trains`          | Add/update a train (needs `password`) |
| POST   | `/api/reserve`        | Book a ticket                         |
| POST   | `/api/cancel`          | Cancel a ticket by `resno`           |
| GET    | `/api/ticket/<resno>` | Look up one reservation               |
| GET    | `/api/tickets`         | List every reservation                |

Default staff password for adding/updating trains: `railway123`
(change `ADMIN_PASSWORD` in `app.py` before deploying this anywhere real).
