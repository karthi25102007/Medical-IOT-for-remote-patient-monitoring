"""Medical IoT Remote Patient Monitoring - Flask backend + MySQL (Workbench)."""
from flask import Flask, request, jsonify, render_template, g
from datetime import datetime
from dateutil import parser as date_parser
import database as db

app = Flask(__name__)


def _parse_ts(s):
    if not s:
        return datetime.now()
    try:
        dt = date_parser.parse(s)
        return dt.replace(tzinfo=None)
    except Exception:
        return datetime.now()


# --- DB lifecycle ---
@app.before_request
def _open():
    g.conn = db.get_connection()

@app.teardown_request
def _close(exc):
    conn = getattr(g, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass

db.init_db()

# --- Pages ---
@app.route("/")
def index():
    return render_template("index.html")

# --- Patient APIs ---
@app.route("/api/patients", methods=["GET"])
def list_patients():
    rows = db.q_all(g.conn, "SELECT * FROM patients ORDER BY id")
    patients = []
    for p in rows:
        latest = db.q_one(
            g.conn,
            "SELECT * FROM vitals WHERE patient_id=%s ORDER BY `timestamp` DESC LIMIT 1",
            (p["id"],),
        )
        p["latest"] = latest
        p["alerts"] = db.check_alert(latest) if latest else []
        patients.append(p)
    return jsonify(patients)

@app.route("/api/patients", methods=["POST"])
def add_patient():
    data = request.get_json(force=True)
    for f in ("name", "age", "gender", "device_id"):
        if not data.get(f):
            return jsonify({"error": f"Missing field: {f}"}), 400
    try:
        lastid, _ = db.execute(
            g.conn,
            "INSERT INTO patients (name, age, gender, `condition`, device_id, created_at)"
            " VALUES (%s,%s,%s,%s,%s,%s)",
            (data["name"], int(data["age"]), data["gender"],
             data.get("condition", ""), data["device_id"], datetime.now()),
        )
    except Exception as e:
        msg = str(e)
        if "Duplicate entry" in msg or "duplicate" in msg.lower():
            return jsonify({"error": "device_id already exists"}), 409
        return jsonify({"error": msg}), 400
    row = db.q_one(g.conn, "SELECT * FROM patients WHERE id=%s", (lastid,))
    return jsonify(row), 201

@app.route("/api/patients/<int:pid>", methods=["GET"])
def get_patient(pid):
    row = db.q_one(g.conn, "SELECT * FROM patients WHERE id=%s", (pid,))
    if not row:
        return jsonify({"error": "Patient not found"}), 404
    row["vitals"] = db.q_all(
        g.conn,
        "SELECT * FROM vitals WHERE patient_id=%s ORDER BY `timestamp` DESC LIMIT 100",
        (pid,),
    )
    return jsonify(row)

@app.route("/api/patients/<int:pid>", methods=["DELETE"])
def delete_patient(pid):
    _, count = db.execute(g.conn, "DELETE FROM patients WHERE id=%s", (pid,))
    if count == 0:
        return jsonify({"error": "Patient not found"}), 404
    return jsonify({"ok": True})

# --- Vitals APIs (IoT ingestion endpoint) ---
@app.route("/api/vitals", methods=["POST"])
def ingest_vitals():
    """IoT devices POST here. Accepts device_id OR patient_id."""
    data = request.get_json(force=True)
    pid = data.get("patient_id")
    if not pid and data.get("device_id"):
        row = db.q_one(g.conn, "SELECT id FROM patients WHERE device_id=%s",
                       (data["device_id"],))
        if row:
            pid = row["id"]
    if not pid:
        return jsonify({"error": "Provide patient_id or valid device_id"}), 400
    if not db.q_one(g.conn, "SELECT id FROM patients WHERE id=%s", (int(pid),)):
        return jsonify({"error": "Patient not found"}), 404
    try:
        vital = {
            "heart_rate": int(data["heart_rate"]),
            "spo2": float(data["spo2"]),
            "temperature": float(data["temperature"]),
            "bp_systolic": int(data.get("bp_systolic", 120)),
            "bp_diastolic": int(data.get("bp_diastolic", 80)),
        }
    except (KeyError, TypeError, ValueError):
        return jsonify({"error": "Required: heart_rate, spo2, temperature, bp_systolic, bp_diastolic"}), 400
    ts = _parse_ts(data.get("timestamp"))
    lastid, _ = db.execute(
        g.conn,
        "INSERT INTO vitals (patient_id, `timestamp`, heart_rate, spo2, temperature, bp_systolic, bp_diastolic)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (int(pid), ts, vital["heart_rate"], vital["spo2"], vital["temperature"],
         vital["bp_systolic"], vital["bp_diastolic"]),
    )
    saved = db.q_one(g.conn, "SELECT * FROM vitals WHERE id=%s", (lastid,))
    saved["alerts"] = db.check_alert(saved)
    return jsonify(saved), 201

@app.route("/api/vitals", methods=["GET"])
def query_vitals():
    pid = request.args.get("patient_id", type=int)
    limit = min(request.args.get("limit", default=50, type=int), 500)
    limit = max(limit, 1)
    if pid:
        rows = db.q_all(
            g.conn,
            f"SELECT * FROM vitals WHERE patient_id=%s ORDER BY `timestamp` DESC LIMIT {limit}",
            (pid,),
        )
    else:
        rows = db.q_all(
            g.conn,
            f"SELECT v.*, p.name AS patient_name, p.device_id FROM vitals v "
            f"JOIN patients p ON p.id=v.patient_id ORDER BY `timestamp` DESC LIMIT {limit}",
        )
    return jsonify(rows)

@app.route("/api/alerts", methods=["GET"])
def alerts():
    """Scan latest reading per patient and return abnormal ones."""
    patients = db.q_all(g.conn, "SELECT * FROM patients")
    out = []
    for p in patients:
        latest = db.q_one(
            g.conn,
            "SELECT * FROM vitals WHERE patient_id=%s ORDER BY `timestamp` DESC LIMIT 1",
            (p["id"],),
        )
        if latest:
            a = db.check_alert(latest)
            if a:
                out.append({"patient_id": p["id"], "patient_name": p["name"],
                            "device_id": p["device_id"], "vital": latest, "alerts": a})
    return jsonify(out)

@app.route("/api/stats", methods=["GET"])
def stats():
    n_pat = db.q_one(g.conn, "SELECT COUNT(*) AS c FROM patients")["c"]
    n_vit = db.q_one(g.conn, "SELECT COUNT(*) AS c FROM vitals")["c"]
    n_dev = db.q_one(g.conn, "SELECT COUNT(DISTINCT device_id) AS c FROM patients")["c"]
    return jsonify({"patients": n_pat, "readings": n_vit, "devices": n_dev,
                    "alerts": len(alerts().get_json())})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
