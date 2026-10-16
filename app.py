import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import RLock

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_FILE = DATA_DIR / "database.json"
DATA_LOCK = RLock()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-development-key")


def _default_data():
    return {
        "settings": {"rate_per_kwh": 8.5},
        "readings": [],
        "next_reading_id": 1
    }


def load_data():
    """Load the local JSON database, creating it on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with DATA_LOCK:
        if not DATA_FILE.exists():
            data = _default_data()
            _write_data(data)
            return data
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"Could not read {DATA_FILE.name}. Check that it contains valid JSON. Details: {exc}"
            ) from exc
        data.setdefault("settings", {})
        data["settings"].setdefault("rate_per_kwh", 8.5)
        data.setdefault("readings", [])
        data.setdefault("next_reading_id", max(
            (int(row.get("id", 0)) for row in data["readings"]), default=0
        ) + 1)
        return data


def _write_data(data):
    """Write atomically so an interrupted save is less likely to corrupt the file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = DATA_FILE.with_suffix(".tmp")
    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")
    temporary_file.replace(DATA_FILE)


def save_data(data):
    with DATA_LOCK:
        _write_data(data)


def _normalise_reading(row):
    result = dict(row)
    result["reading_date"] = datetime.strptime(
        result["reading_date"], "%Y-%m-%d"
    ).date()
    result["consumption_kwh"] = float(result["consumption_kwh"])
    result["expected_kwh"] = float(result["expected_kwh"])
    result["id"] = int(result["id"])
    return result


def classify(consumption, expected):
    if expected <= 0:
        return "Check baseline"
    ratio = consumption / expected
    if ratio >= 1.5:
        return "High"
    if ratio >= 1.2:
        return "Warning"
    return "Normal"


def get_rate():
    data = load_data()
    try:
        return float(data["settings"].get("rate_per_kwh", 8.5))
    except (ValueError, TypeError):
        return 8.5


def get_readings():
    data = load_data()
    rows = [_normalise_reading(row) for row in data["readings"]]
    return sorted(rows, key=lambda row: (row["reading_date"], row["id"]), reverse=True)


def add_demo_data():
    data = load_data()
    if data["readings"]:
        return
    today = date.today()
    samples = [
        ("Main Building", "Classroom 101", "MTR-MB-101", 12.5, 12.0, "Normal classroom usage"),
        ("Main Building", "Classroom 102", "MTR-MB-102", 23.0, 13.0, "Unexpected high reading; inspect equipment"),
        ("Science Block", "Computer Lab", "MTR-SB-LAB", 38.0, 32.0, "Computer lab usage"),
        ("Library", "Reading Hall", "MTR-LIB-01", 16.0, 18.0, "Within expected range"),
        ("Main Building", "Classroom 201", "MTR-MB-201", 11.0, 12.0, "Normal classroom usage"),
    ]
    for i, sample in enumerate(samples):
        building, room, meter, actual, expected, notes = sample
        data["readings"].append({
            "id": data["next_reading_id"],
            "reading_date": (today - timedelta(days=i)).isoformat(),
            "building": building,
            "room": room,
            "meter_id": meter,
            "consumption_kwh": actual,
            "expected_kwh": expected,
            "notes": notes,
            "created_at": datetime.now().isoformat(timespec="seconds")
        })
        data["next_reading_id"] += 1
    save_data(data)


@app.route("/")
def dashboard():
    all_rows = get_readings()
    rate = get_rate()
    total_kwh = sum(row["consumption_kwh"] for row in all_rows)
    expected_total = sum(row["expected_kwh"] for row in all_rows)
    totals = {
        "readings_count": len(all_rows),
        "total_kwh": total_kwh,
        "estimated_cost": total_kwh * rate,
        "expected_kwh": expected_total
    }
    high_count = sum(
        1 for row in all_rows
        if row["consumption_kwh"] >= row["expected_kwh"] * 1.5
    )
    rows = all_rows[:8]

    cutoff = date.today() - timedelta(days=14)
    by_date = {}
    by_building_totals = {}
    alerts = []
    for row in all_rows:
        day = row["reading_date"]
        if day >= cutoff:
            entry = by_date.setdefault(day, {"actual": 0.0, "expected": 0.0})
            entry["actual"] += row["consumption_kwh"]
            entry["expected"] += row["expected_kwh"]
        by_building_totals[row["building"]] = (
            by_building_totals.get(row["building"], 0.0) + row["consumption_kwh"]
        )
        if row["expected_kwh"] > 0 and row["consumption_kwh"] >= row["expected_kwh"] * 1.2:
            alert = dict(row)
            alert["status"] = classify(row["consumption_kwh"], row["expected_kwh"])
            alert["ratio"] = round(row["consumption_kwh"] / row["expected_kwh"] * 100)
            alerts.append(alert)

    chart_rows = sorted(by_date.items())
    labels = [day.strftime("%d %b") for day, _ in chart_rows]
    actual = [round(values["actual"], 2) for _, values in chart_rows]
    expected = [round(values["expected"], 2) for _, values in chart_rows]
    by_building = [
        {"building": building, "total": total}
        for building, total in sorted(
            by_building_totals.items(), key=lambda item: item[1], reverse=True
        )[:6]
    ]
    alerts.sort(
        key=lambda row: (
            row["consumption_kwh"] / row["expected_kwh"] if row["expected_kwh"] else 0,
            row["reading_date"]
        ),
        reverse=True
    )
    for row in rows:
        row["status"] = classify(row["consumption_kwh"], row["expected_kwh"])
    return render_template(
        "dashboard.html", totals=totals, high_count=high_count, rate=rate,
        rows=rows, labels=labels, actual=actual, expected=expected,
        by_building=by_building, alerts=alerts[:5]
    )


@app.route("/readings")
def readings():
    search = request.args.get("q", "").strip().casefold()
    rows = get_readings()
    if search:
        rows = [
            row for row in rows
            if search in row["building"].casefold()
            or search in row["room"].casefold()
            or search in row["meter_id"].casefold()
        ]
    for row in rows:
        row["status"] = classify(row["consumption_kwh"], row["expected_kwh"])
    return render_template("readings.html", rows=rows, q=request.args.get("q", "").strip())


@app.route("/readings/add", methods=["GET", "POST"])
def add_reading():
    if request.method == "POST":
        try:
            reading_date = request.form.get("reading_date", "").strip()
            building = request.form.get("building", "").strip()
            room = request.form.get("room", "").strip()
            meter_id = request.form.get("meter_id", "").strip()
            consumption = float(request.form.get("consumption_kwh", ""))
            expected = float(request.form.get("expected_kwh", ""))
            notes = request.form.get("notes", "").strip()
            if not all([reading_date, building, room, meter_id]):
                raise ValueError("Please fill in all required fields.")
            datetime.strptime(reading_date, "%Y-%m-%d")
            if len(building) > 100 or len(room) > 100 or len(meter_id) > 80 or len(notes) > 500:
                raise ValueError("One or more text fields exceed the allowed length.")
            if consumption < 0 or expected <= 0:
                raise ValueError("Consumption cannot be negative and expected usage must be greater than zero.")
            data = load_data()
            new_id = int(data["next_reading_id"])
            data["readings"].append({
                "id": new_id,
                "reading_date": reading_date,
                "building": building,
                "room": room,
                "meter_id": meter_id,
                "consumption_kwh": round(consumption, 2),
                "expected_kwh": round(expected, 2),
                "notes": notes,
                "created_at": datetime.now().isoformat(timespec="seconds")
            })
            data["next_reading_id"] = new_id + 1
            save_data(data)
            status = classify(consumption, expected)
            if status in ("High", "Warning"):
                flash(
                    f"Reading saved. {status} usage detected ({consumption:g} kWh vs expected {expected:g} kWh).",
                    "warning"
                )
            else:
                flash("Electricity reading saved successfully.", "success")
            return redirect(url_for("readings"))
        except ValueError as exc:
            flash(str(exc) or "Please enter valid values.", "danger")
        except (OSError, RuntimeError) as exc:
            flash(f"Could not save the JSON database: {exc}", "danger")
    return render_template("add_reading.html", today=date.today().isoformat())


@app.route("/readings/<int:reading_id>/delete", methods=["POST"])
def delete_reading(reading_id):
    data = load_data()
    original_count = len(data["readings"])
    data["readings"] = [
        row for row in data["readings"] if int(row.get("id", -1)) != reading_id
    ]
    if len(data["readings"]) != original_count:
        save_data(data)
        flash("Reading deleted.", "success")
    else:
        flash("Reading not found.", "warning")
    return redirect(url_for("readings"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            rate = float(request.form.get("rate_per_kwh", ""))
            if rate < 0:
                raise ValueError
            data = load_data()
            data["settings"]["rate_per_kwh"] = round(rate, 2)
            save_data(data)
            flash("Settings updated.", "success")
            return redirect(url_for("settings"))
        except (ValueError, OSError, RuntimeError):
            flash("Enter a valid non-negative electricity rate.", "danger")
    return render_template("settings.html", rate=get_rate())


@app.route("/api/summary")
def api_summary():
    rate = get_rate()
    total_kwh = sum(row["consumption_kwh"] for row in get_readings())
    return jsonify({
        "total_kwh": round(total_kwh, 2),
        "rate_per_kwh": rate,
        "estimated_cost": round(total_kwh * rate, 2),
        "storage": "JSON file"
    })


@app.errorhandler(RuntimeError)
def storage_error(error):
    return render_template(
        "error.html",
        message=str(error),
        help_text="Check that data/database.json is valid JSON and the project folder is writable."
    ), 500


@app.route("/health")
def health():
    return {"status": "ok", "application": "Smart Electricity Consumption Management System", "database": "JSON"}


if __name__ == "__main__":
    try:
        load_data()
        add_demo_data()
    except (OSError, RuntimeError) as exc:
        print("\nJSON DATABASE INITIALIZATION FAILED")
        print(f"Details: {exc}")
        print("Check that the project folder is writable and data/database.json is valid JSON.")
        raise SystemExit(1)
    print("JSON database ready. Open http://127.0.0.1:5000")
    app.run(debug=True)
