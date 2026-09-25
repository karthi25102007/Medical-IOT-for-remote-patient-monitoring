"""Simulate an IoT wearable sending vitals to the Flask server."""
import random, time, requests

BASE = "http://localhost:5000"
DEVICE_ID = "IOT-WATCH-001"  # change to any registered device_id

def read_sensor():
    return {
        "device_id": DEVICE_ID,
        "heart_rate": random.randint(60, 105),
        "spo2": round(random.uniform(93, 99.5), 1),
        "temperature": round(random.uniform(36.0, 37.8), 1),
        "bp_systolic": random.randint(110, 145),
        "bp_diastolic": random.randint(70, 92),
    }

if __name__ == "__main__":
    print(f"Sending simulated vitals for {DEVICE_ID} every 5s (Ctrl+C to stop)...")
    while True:
        payload = read_sensor()
        try:
            r = requests.post(f"{BASE}/api/vitals", json=payload, timeout=5)
            print(r.status_code, r.json())
        except Exception as e:
            print("Server not reachable:", e)
        time.sleep(5)
