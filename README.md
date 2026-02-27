# PRISM

Parking Resource Intelligence and Slot Management (PRISM) is a smart parking mini project that combines IoT sensors, MQTT messaging, and a Flask backend for real-time slot visibility.

## Current Scope (Day 1 Baseline)

This repository currently contains the Day 1 foundation:

- project structure for hardware, backend, frontend, ML, data, and docs
- Flask backend app factory with REST endpoints
- SQLAlchemy models for users, lots, zones, slots, and occupancy logging
- MQTT subscriber service for sensor data ingestion
- Arduino sketches for TinkerCAD simulation and ESP32 firmware

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
├── hardware/
│   ├── esp32/
│   ├── schematics/
│   └── tinkercad/
├── data/
├── docs/
├── frontend/
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

## Project Documentation

- Day 1 closure verification: [`docs/day1_closure_report.md`](docs/day1_closure_report.md)
- MQTT contract: [`docs/mqtt_topics.md`](docs/mqtt_topics.md)

## Backend Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
FLASK_APP=app flask db upgrade
python run.py
```

## Next Planned Modules

- authentication routes (JWT)
- prediction and recommendation endpoints
- frontend dashboard implementation
- full migration history and tests expansion
