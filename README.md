# PRISM

Parking Resource Intelligence and Slot Management (PRISM) is a smart parking system combining IoT sensors, MQTT messaging, and a Flask backend for real-time slot visibility.

## Features

- Flask backend with REST API
- SQLAlchemy models for users, lots, zones, slots, and occupancy logging
- MQTT subscriber service for sensor data ingestion
- Next.js dashboard with real-time slot monitoring UI
- Arduino/ESP32 firmware for ultrasonic distance sensors
- Multi-sensor simulation for TinkerCAD validation

## Repository Structure

```text
prism/
├── backend/
│   ├── app/
│   │   ├── models/
│   │   ├── routes/
│   │   └── services/
│   ├── migrations/
│   ├── tests/
│   ├── .env.example
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/
│       ├── app/          # Next.js pages (dashboard, lots, activity, settings)
│       ├── components/   # Shared UI components
│       ├── lib/          # API client, formatting, mock data
│       └── types/        # TypeScript interfaces
├── hardware/
│   ├── esp32/
│   ├── schematics/
│   └── tinkercad/
├── data/
├── docs/
├── ml/
└── scripts/
```

## Implemented API Endpoints

### Health
- `GET /`
- `GET /health`

### Lots
- `GET /api/v1/lots`
- `POST /api/v1/lots`
- `GET /api/v1/lots/<lot_id>`
- `GET /api/v1/lots/summary`

### Slots
- `GET /api/v1/slots`
- `GET /api/v1/slots/<slot_id>`
- `PUT /api/v1/slots/<slot_id>/status`
- `GET /api/v1/slots/<slot_id>/events`

## MQTT Topic Contract

Topic conventions are documented in [`docs/mqtt_topics.md`](docs/mqtt_topics.md).

## Branch Policy

- `develop` is the active development branch.
- `main` receives stable, reviewed merges only.
- Feature and experiment work should be isolated in short-lived branches.

## Documentation

- MQTT contract: [`docs/mqtt_topics.md`](docs/mqtt_topics.md)
- Hardware assembly guide: [`docs/hardware_assembly_guide.md`](docs/hardware_assembly_guide.md)
- Wiring diagrams: [`docs/wiring_diagram.md`](docs/wiring_diagram.md)
- Day 5 simulator integration report: [`docs/day5_full_stack_simulator_test.md`](docs/day5_full_stack_simulator_test.md)

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
FLASK_APP=app flask db upgrade
python run.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000` to view the dashboard.

## Testing

```bash
# MQTT connectivity test
python3 tests/test_mqtt_integration.py

# Run all tests
pytest tests/ -v
```
