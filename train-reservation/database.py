"""
database.py
Handles all SQLite database setup and queries for the Train Reservation System.
This replaces the original C++ program's raw binary file I/O
(Train1.dat / Ticket1.dat) with a proper relational database.
"""

import sqlite3
import os
import random

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train_reservation.db")

# Class codes map to the five seat categories from the original program
CLASS_NAMES = {
    "AF": "A/C First Class",
    "AS": "A/C Second Class",
    "FS": "First Class Sleeper",
    "AC": "A/C Chair Car",
    "SS": "Second Class Sleeper",
}

# Maps a class code to the column in the trains table that stores its seat count
CLASS_SEAT_COLUMN = {
    "AF": "af_seats",
    "AS": "as_seats",
    "FS": "fs_seats",
    "AC": "ac_seats",
    "SS": "ss_seats",
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if they do not already exist."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS trains (
            trainno INTEGER PRIMARY KEY,
            trainname TEXT NOT NULL,
            startingpoint TEXT NOT NULL,
            destination TEXT NOT NULL,
            af_seats INTEGER NOT NULL DEFAULT 0,
            as_seats INTEGER NOT NULL DEFAULT 0,
            fs_seats INTEGER NOT NULL DEFAULT 0,
            ac_seats INTEGER NOT NULL DEFAULT 0,
            ss_seats INTEGER NOT NULL DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            resno INTEGER PRIMARY KEY AUTOINCREMENT,
            trainno INTEGER NOT NULL,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            class_code TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'confirmed',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (trainno) REFERENCES trains (trainno)
        )
    """)

    conn.commit()
    conn.close()


def seed_if_empty():
    """Add a couple of sample trains on first run so the site isn't empty."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM trains")
    count = cur.fetchone()["c"]
    if count == 0:
        sample_trains = [
            (12951, "Mumbai Rajdhani Express", "Mumbai Central", "New Delhi", 20, 30, 40, 50, 60),
            (12301, "Howrah Rajdhani Express", "Howrah", "New Delhi", 15, 25, 35, 45, 55),
            (12621, "Tamil Nadu Express", "Chennai Central", "New Delhi", 10, 20, 30, 40, 50),
        ]
        cur.executemany(
            """INSERT INTO trains
               (trainno, trainname, startingpoint, destination, af_seats, as_seats, fs_seats, ac_seats, ss_seats)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sample_trains,
        )
        conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Train operations  (menu options 1 & 2 in the original program)
# ---------------------------------------------------------------------------

def get_all_trains():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM trains ORDER BY trainno").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_train(trainno):
    conn = get_connection()
    row = conn.execute("SELECT * FROM trains WHERE trainno = ?", (trainno,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_train(data):
    """Add or update a train's details (was 'UPDATE TRAIN DETAILS' in the original)."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO trains
           (trainno, trainname, startingpoint, destination, af_seats, as_seats, fs_seats, ac_seats, ss_seats)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(trainno) DO UPDATE SET
               trainname=excluded.trainname,
               startingpoint=excluded.startingpoint,
               destination=excluded.destination,
               af_seats=excluded.af_seats,
               as_seats=excluded.as_seats,
               fs_seats=excluded.fs_seats,
               ac_seats=excluded.ac_seats,
               ss_seats=excluded.ss_seats
        """,
        (
            data["trainno"], data["trainname"], data["startingpoint"], data["destination"],
            data["af_seats"], data["as_seats"], data["fs_seats"], data["ac_seats"], data["ss_seats"],
        ),
    )
    conn.commit()
    conn.close()


def delete_train(trainno):
    conn = get_connection()
    conn.execute("DELETE FROM trains WHERE trainno = ?", (trainno,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Ticket operations (menu options 3, 4 & 5 in the original program)
# ---------------------------------------------------------------------------

def count_confirmed(trainno, class_code):
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM tickets WHERE trainno = ? AND class_code = ? AND status = 'confirmed'",
        (trainno, class_code),
    ).fetchone()
    conn.close()
    return row["c"]


def reserve_ticket(trainno, name, age, class_code):
    """
    Mirrors tickets::reservation() from the original program:
    - looks up the train
    - checks remaining seats in the chosen class
    - status is 'confirmed' if a seat is free, otherwise 'waitlisted'
    - a random reservation-style reference is also generated for display,
      matching the original's use of rand() for the reservation number feel
    """
    train = get_train(trainno)
    if not train:
        return None

    seat_column = CLASS_SEAT_COLUMN[class_code]
    total_seats = train[seat_column]
    already_booked = count_confirmed(trainno, class_code)

    status = "confirmed" if already_booked < total_seats else "waitlisted"

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO tickets (trainno, name, age, class_code, status)
           VALUES (?, ?, ?, ?, ?)""",
        (trainno, name, age, class_code, status),
    )
    conn.commit()
    resno = cur.lastrowid
    row = conn.execute("SELECT * FROM tickets WHERE resno = ?", (resno,)).fetchone()
    conn.close()
    return dict(row)


def cancel_ticket(resno):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tickets WHERE resno = ?", (resno,)).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute("UPDATE tickets SET status = 'cancelled' WHERE resno = ?", (resno,))
    conn.commit()

    # If a confirmed seat just freed up, promote the oldest waitlisted
    # passenger on the same train/class -- a small, sensible improvement
    # over the original program, which had no such promotion logic.
    if row["status"] == "confirmed":
        next_waiting = conn.execute(
            """SELECT resno FROM tickets
               WHERE trainno = ? AND class_code = ? AND status = 'waitlisted'
               ORDER BY resno ASC LIMIT 1""",
            (row["trainno"], row["class_code"]),
        ).fetchone()
        if next_waiting:
            conn.execute(
                "UPDATE tickets SET status = 'confirmed' WHERE resno = ?",
                (next_waiting["resno"],),
            )
            conn.commit()
    conn.close()
    return True


def get_ticket(resno):
    conn = get_connection()
    row = conn.execute(
        """SELECT tickets.*, trains.trainname, trains.startingpoint, trains.destination
           FROM tickets JOIN trains ON tickets.trainno = trains.trainno
           WHERE tickets.resno = ?""",
        (resno,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_tickets():
    conn = get_connection()
    rows = conn.execute(
        """SELECT tickets.*, trains.trainname
           FROM tickets JOIN trains ON tickets.trainno = trains.trainno
           ORDER BY tickets.resno DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
