"""
app.py
Flask backend for the Railway Ticket Reservation web app.

This is a faithful web re-implementation of the original Turbo C++ console
program (train + tickets classes, and the 6-option main menu). Binary file
storage (Train1.dat / Ticket1.dat) has been replaced with a SQLite database,
and the gotoxy()-driven console screens have been replaced with a browser UI
talking to this JSON API.

Run with:  python app.py
Then open: http://127.0.0.1:5000
"""

from flask import Flask, jsonify, request, render_template
import database as db

app = Flask(__name__)

# In the original program, option 2 ("UPDATE TRAIN DETAILS") asked for a
# password before letting staff add/edit a train. We keep that idea but
# make it an actual check (the original asked for it but never validated it).
ADMIN_PASSWORD = "railway123"


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Trains  -->  menu option 1 (view) and 2 (add/update, password protected)
# ---------------------------------------------------------------------------

@app.route("/api/classes", methods=["GET"])
def api_classes():
    return jsonify(db.CLASS_NAMES)


@app.route("/api/trains", methods=["GET"])
def api_get_trains():
    return jsonify(db.get_all_trains())


@app.route("/api/trains/<int:trainno>", methods=["GET"])
def api_get_train(trainno):
    train = db.get_train(trainno)
    if not train:
        return jsonify({"error": "No train found with that number."}), 404
    availability = {}
    for code, col in db.CLASS_SEAT_COLUMN.items():
        booked = db.count_confirmed(trainno, code)
        availability[code] = {
            "total": train[col],
            "booked": booked,
            "available": max(train[col] - booked, 0),
        }
    train["availability"] = availability
    return jsonify(train)


@app.route("/api/trains", methods=["POST"])
def api_add_train():
    payload = request.get_json(force=True, silent=True) or {}

    if payload.get("password") != ADMIN_PASSWORD:
        return jsonify({"error": "Incorrect password."}), 401

    required = ["trainno", "trainname", "startingpoint", "destination",
                "af_seats", "as_seats", "fs_seats", "ac_seats", "ss_seats"]
    missing = [f for f in required if f not in payload or str(payload[f]).strip() == ""]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        data = {
            "trainno": int(payload["trainno"]),
            "trainname": str(payload["trainname"]).strip(),
            "startingpoint": str(payload["startingpoint"]).strip(),
            "destination": str(payload["destination"]).strip(),
            "af_seats": int(payload["af_seats"]),
            "as_seats": int(payload["as_seats"]),
            "fs_seats": int(payload["fs_seats"]),
            "ac_seats": int(payload["ac_seats"]),
            "ss_seats": int(payload["ss_seats"]),
        }
    except (ValueError, TypeError):
        return jsonify({"error": "Train number and seat counts must be numbers."}), 400

    if any(data[f] < 0 for f in ["af_seats", "as_seats", "fs_seats", "ac_seats", "ss_seats"]):
        return jsonify({"error": "Seat counts cannot be negative."}), 400

    db.add_train(data)
    return jsonify({"message": "Train details saved.", "train": db.get_train(data["trainno"])}), 201


# ---------------------------------------------------------------------------
# Reservation  -->  menu option 3
# ---------------------------------------------------------------------------

@app.route("/api/reserve", methods=["POST"])
def api_reserve():
    payload = request.get_json(force=True, silent=True) or {}

    try:
        trainno = int(payload.get("trainno"))
        name = str(payload.get("name", "")).strip()
        age = int(payload.get("age"))
        class_code = str(payload.get("class_code", "")).strip().upper()
    except (ValueError, TypeError):
        return jsonify({"error": "Train number and age must be numbers."}), 400

    if not name:
        return jsonify({"error": "Passenger name is required."}), 400
    if age <= 0 or age > 130:
        return jsonify({"error": "Please enter a valid age."}), 400
    if class_code not in db.CLASS_NAMES:
        return jsonify({"error": "Please select a valid travel class."}), 400

    if not db.get_train(trainno):
        return jsonify({"error": "No train found with that number."}), 404

    ticket = db.reserve_ticket(trainno, name, age, class_code)
    ticket["class_name"] = db.CLASS_NAMES[class_code]
    return jsonify(ticket), 201


# ---------------------------------------------------------------------------
# Cancellation  -->  menu option 4
# ---------------------------------------------------------------------------

@app.route("/api/cancel", methods=["POST"])
def api_cancel():
    payload = request.get_json(force=True, silent=True) or {}
    try:
        resno = int(payload.get("resno"))
    except (ValueError, TypeError):
        return jsonify({"error": "Enter a valid reservation number."}), 400

    ticket = db.get_ticket(resno)
    if not ticket:
        return jsonify({"error": "No such reservation is made. Please retry."}), 404
    if ticket["status"] == "cancelled":
        return jsonify({"error": "That reservation is already cancelled."}), 400

    db.cancel_ticket(resno)
    return jsonify({"message": "Reservation cancelled."})


# ---------------------------------------------------------------------------
# Display ticket status  -->  menu option 5
# ---------------------------------------------------------------------------

@app.route("/api/ticket/<int:resno>", methods=["GET"])
def api_get_ticket(resno):
    ticket = db.get_ticket(resno)
    if not ticket:
        return jsonify({"error": "Unrecognized reservation number."}), 404
    ticket["class_name"] = db.CLASS_NAMES.get(ticket["class_code"], ticket["class_code"])
    return jsonify(ticket)


@app.route("/api/tickets", methods=["GET"])
def api_get_all_tickets():
    tickets = db.get_all_tickets()
    for t in tickets:
        t["class_name"] = db.CLASS_NAMES.get(t["class_code"], t["class_code"])
    return jsonify(tickets)


if __name__ == "__main__":
    db.init_db()
    db.seed_if_empty()
    app.run(debug=True)
