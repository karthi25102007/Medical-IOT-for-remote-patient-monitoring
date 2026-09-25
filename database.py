"""MySQL database layer for Medical IoT Remote Patient Monitoring.
Works with MySQL Workbench (MySQL Server 8.0).
Settings live in db_config.py. Schema also in schema.sql.
"""
import mysql.connector
from mysql.connector import Error as MySQLError
from datetime import datetime, timedelta
from decimal import Decimal
import random
import db_config

SCHEMA_DB = f"CREATE DATABASE IF NOT EXISTS `{db_config.MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"

SCHEMA_PATIENTS = """
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    gender VARCHAR(20) NOT NULL,
    `condition` VARCHAR(200) DEFAULT '',
    device_id VARCHAR(50) UNIQUE NOT NULL,
    created_at DATETIME NOT NULL
) ENGINE=InnoDB
"""

SCHEMA_VITALS = """
CREATE TABLE IF NOT EXISTS vitals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    `timestamp` DATETIME NOT NULL,
    heart_rate INT NOT NULL,
    spo2 DECIMAL(4,1) NOT NULL,
    temperature DECIMAL(4,1) NOT NULL,
    bp_systolic INT NOT NULL,
    bp_diastolic INT NOT NULL,
    CONSTRAINT fk_vitals_patient FOREIGN KEY (patient_id)
        REFERENCES patients(id) ON DELETE CASCADE,
    INDEX idx_vitals_patient_time (patient_id, `timestamp` DESC)
) ENGINE=InnoDB
"""


def _base_kwargs(include_db=True):
    kw = {
        "host": db_config.MYSQL_HOST,
        "port": db_config.MYSQL_PORT,
        "user": db_config.MYSQL_USER,
        "password": db_config.MYSQL_PASSWORD,
    }
    if include_db:
        kw["database"] = db_config.MYSQL_DB
    return kw


def get_connection(include_db=True):
    return mysql.connector.connect(**_base_kwargs(include_db))


def _norm(row):
    """Convert MySQL types (datetime, Decimal) to JSON-friendly values."""
    if row is None:
        return None
    d = dict(row)
    for k, v in list(d.items()):
        if isinstance(v, datetime):
            d[k] = v.isoformat(sep=" ")
        elif isinstance(v, Decimal):
            d[k] = float(v)
        elif isinstance(v, timedelta):
            d[k] = str(v)
    # `condition` is a reserved word in some contexts; keep key as-is
    return d


def q_one(conn, sql, params=None):
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return _norm(cur.fetchone())
    finally:
        cur.close()


def q_all(conn, sql, params=None):
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql, params or ())
        return [_norm(r) for r in cur.fetchall()]
    finally:
        cur.close()


def execute(conn, sql, params=None):
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        lastid = cur.lastrowid
        count = cur.rowcount
        conn.commit()
        return lastid, count
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def init_db(seed=True):
    # 1. create database
    srv = get_connection(include_db=False)
    cur = srv.cursor()
    try:
        cur.execute(SCHEMA_DB)
        srv.commit()
    finally:
        cur.close()
        srv.close()
    # 2. create tables
    conn = get_connection(include_db=True)
    cur = conn.cursor()
    try:
        cur.execute(SCHEMA_PATIENTS)
        cur.execute(SCHEMA_VITALS)
        conn.commit()
    finally:
        cur.close()
    # 3. seed demo data if empty
    try:
        row = q_one(conn, "SELECT COUNT(*) AS c FROM patients")
        if row and row["c"] == 0 and seed:
            demo = [
                ("Aarav Sharma", 67, "Male", "Hypertension", "IOT-WATCH-001"),
                ("Priya Patel", 54, "Female", "Type 2 Diabetes", "IOT-WATCH-002"),
                ("John Carter", 72, "Male", "Post-Cardiac Surgery", "IOT-PATCH-003"),
            ]
            now = datetime.now()
            cur = conn.cursor()
            try:
                for name, age, gender, cond, dev in demo:
                    cur.execute(
                        "INSERT INTO patients (name, age, gender, `condition`, device_id, created_at)"
                        " VALUES (%s,%s,%s,%s,%s,%s)",
                        (name, age, gender, cond, dev, now),
                    )
                    pid = cur.lastrowid
                    for h in range(24, 0, -1):
                        ts = now - timedelta(hours=h)
                        cur.execute(
                            "INSERT INTO vitals (patient_id, `timestamp`, heart_rate, spo2, temperature, bp_systolic, bp_diastolic)"
                            " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                            (pid, ts, random.randint(62, 98), round(random.uniform(95, 99.5), 1),
                             round(random.uniform(36.1, 37.4), 1), random.randint(110, 140), random.randint(70, 90)),
                        )
                conn.commit()
            finally:
                cur.close()
    finally:
        conn.close()


def check_alert(v):
    """Return list of alert strings for a vital reading."""
    alerts = []
    try:
        hr = v.get("heart_rate")
        spo2 = v.get("spo2")
        temp = v.get("temperature")
        sys = v.get("bp_systolic")
        dia = v.get("bp_diastolic")
        hr = float(hr) if hr is not None else None
        spo2 = float(spo2) if spo2 is not None else None
        temp = float(temp) if temp is not None else None
        sys = float(sys) if sys is not None else None
        dia = float(dia) if dia is not None else None
    except (TypeError, ValueError):
        return alerts
    if hr is not None and (hr < 50 or hr > 120):
        alerts.append(f"Abnormal heart rate: {v.get('heart_rate')} bpm")
    if spo2 is not None and spo2 < 92:
        alerts.append(f"Low SpO2: {v.get('spo2')}%")
    if temp is not None and (temp > 38.0 or temp < 35.0):
        alerts.append(f"Abnormal temperature: {v.get('temperature')} C")
    if sys is not None and (sys > 180 or sys < 80):
        alerts.append(f"Abnormal systolic BP: {v.get('bp_systolic')} mmHg")
    if dia is not None and (dia > 120 or dia < 50):
        alerts.append(f"Abnormal diastolic BP: {v.get('bp_diastolic')} mmHg")
    return alerts
