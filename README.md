# 🩺 MediTrack IoT — Remote Patient Monitoring (Python + MySQL Workbench)

Wearables POST vitals (heart rate, SpO2, temperature, BP) to a Python Flask API
backed by **MySQL** (`medical_iot` database, viewable in MySQL Workbench),
and doctors monitor patients live in the browser.

## Why MySQL (not SQLite)?
- SQLite = single file `medical.db`, good for demo only, 1 user at a time.
- MySQL + Workbench = real client-server DB: multi-user, passwords, larger data,
  visual tables in Workbench, proper DATETIME/DECIMAL types, what teachers expect.

## Project files
```
assignment 3/
├── app.py               # Flask server + REST API (MySQL)
├── database.py          # MySQL connector, auto-create DB/tables, seed, alerts
├── db_config.py         # MySQL host/user/password  <-- set your password here
├── schema.sql           # run in Workbench to create medical_iot manually
├── simulate_device.py   # fake IoT wearable sender
├── requirements.txt
├── templates/index.html
└── static/css/style.css + static/js/dashboard.js
```

## MySQL setup (Workbench)
1. Open MySQL Workbench, connect as `root` (password in `db_config.py`).
2. Option A (auto): just run the website — `database.py:init_db()` creates
   `medical_iot` + tables + 3 demo patients automatically.
3. Option B (manual): open `schema.sql` in Workbench and Execute (lightning icon).
4. Verify: Schemas → `medical_iot` → Tables → `patients`, `vitals` →
   `SELECT * FROM medical_iot.patients;`

## Run
```powershell
cd "C:\Users\Admin\OneDrive\Desktop\assignment 3"
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```

Simulate a wearable (second terminal):
```powershell
python simulate_device.py
```

## REST API
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/patients` | list patients + latest vital + alerts |
| POST | `/api/patients` | register `{name, age, gender, condition, device_id}` |
| GET | `/api/patients/<id>` | patient + last 100 vitals |
| DELETE | `/api/patients/<id>` | remove patient |
| POST | `/api/vitals` | **IoT ingestion** `{device_id|patient_id, heart_rate, spo2, temperature, bp_systolic, bp_diastolic}` |
| GET | `/api/vitals?patient_id=1&limit=50` | query readings |
| GET | `/api/alerts` | abnormal latest readings |
| GET | `/api/stats` | counts |

Alert thresholds: HR <50 or >120, SpO2 <92%, Temp >38 / <35 C, Sys >180/<80, Dia >120/<50.
