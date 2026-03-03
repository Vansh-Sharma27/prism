# Day 7 End-to-End Simulator Test Report

## Objective

Validate full Phase 1 flow with simulated hardware data:

1. Register a new user
2. Login and fetch dashboard data
3. Start simulator publishing
4. Confirm live occupancy updates and events

## Environment

- Date: 2026-03-03
- Backend: Flask (`backend/run.py`)
- Frontend: Next.js (`frontend`)
- MQTT broker: Mosquitto (`localhost:1883`)
- Simulator: `hardware/simulator/mqtt_simulator.py --mode dynamic`

## Test Preparation

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
flask seed-campus --admin-email admin@prism.local --admin-password Admin@12345
```

## Execution Steps

### 1) Start backend

```bash
cd backend
python run.py
```

Expected:

- Backend starts on `http://0.0.0.0:5000`
- MQTT subscriber connects successfully

### 2) Start frontend

```bash
cd frontend
npm install
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Expected:

- Frontend available at `http://<vm-ip>:3000`
- Login/register pages render

### 3) Start simulator

```bash
cd hardware/simulator
python mqtt_simulator.py --mode dynamic --interval 2 --cycles 60
```

Expected:

- Slot updates published to `prism/lot-a/slot/slot-1..slot-6`
- Heartbeats published to `prism/lot-a/heartbeat`
- MQTT ingestion maps topic slot IDs to backend IDs (`lot-a-slot-1..lot-a-slot-6`)

### 4) Register and login

Register:

```bash
curl -s -X POST http://localhost:5000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"day7.student@gla.ac.in","password":"StrongPass123"}'
```

Login:

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"day7.student@gla.ac.in","password":"StrongPass123"}' | jq -r '.access_token')
```

### 5) Verify live data path

```bash
# Lots and summary
curl -s http://localhost:5000/api/v1/lots -H "Authorization: Bearer $TOKEN"
curl -s http://localhost:5000/api/v1/lots/summary -H "Authorization: Bearer $TOKEN"

# Event stream
curl -s "http://localhost:5000/api/v1/events?lot_id=lot-a&limit=20" \
  -H "Authorization: Bearer $TOKEN"
```

Expected:

- At least one slot in `lot-a` flips occupied/vacant while simulator runs
- `/api/v1/events` returns entry/exit rows
- Dashboard `/` reflects updated counts after polling cycle

## Evidence Summary

Automated checks:

- `pytest tests/test_seed_campus.py tests/test_day7_e2e_simulator_flow.py tests/test_auth_security.py -v` passed (`6 passed`).

Runtime sample (captured on 2026-03-03 UTC):

- Register response code: `201`
- Login response code: `200`
- Slot update response code: `200`
- Updated slot: `lot-a-slot-3`
- Lots summary before update:
  - `total_slots: 12`
  - `available_slots: 8`
  - `occupied_slots: 4`
  - `occupancy_rate: 33.3`
- Lots summary after update:
  - `total_slots: 12`
  - `available_slots: 7`
  - `occupied_slots: 5`
  - `occupancy_rate: 41.7`
- `/api/v1/events?lot_id=lot-a&limit=3` returned live simulator + API-triggered events (event IDs `2775-2777` in sample run).

## Result

Day 7 end-to-end simulator flow is validated for:

- Registration and login
- Authenticated lot/slot/event reads
- Live occupancy change ingestion
- Dashboard-ready aggregate updates
