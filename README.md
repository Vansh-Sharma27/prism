# PRISM

Parking Resource Intelligence and Slot Management (PRISM) is a smart parking system combining IoT sensors, MQTT messaging, a Flask REST backend, a Next.js dashboard, and machine learning predictions for real-time parking slot visibility and occupancy forecasting.

## Features

### Core Platform
- Flask REST API with SQLAlchemy ORM (PostgreSQL)
- Next.js 16 + TypeScript dashboard with real-time slot monitoring
- Arduino/ESP32 firmware for ultrasonic distance sensors (HC-SR04)
- Multi-sensor simulation with day-part occupancy patterns and dataset export

### Machine Learning
- Zone-level occupancy prediction using RandomForestRegressor (R-squared = 0.89, MAE = 4.69%)
- PredictionService with graceful fallback to rule-based heuristic when model is unavailable
- 11 engineered features: temporal, cyclical encoding, lag, and rolling averages
- Training pipeline combining synthetic data with KLCC real-world dataset

### Security and Auth
- JWT authentication with RBAC (student, faculty, admin roles)
- Rate limiting configurable per endpoint (backed by Redis)
- CORS policy with configurable allowed origins
- ProxyFix middleware for reverse proxy deployments
- SHA-256 model file verification on load
- Structured JSON logging with per-request `request_id` tracing

### Real-Time
- MQTT subscriber service for sensor data ingestion
- SSE (Server-Sent Events) notification stream for live slot changes
- Redis-backed pub/sub notification broker

## Repository Structure

```text
prism/
├── .github/
│   └── workflows/
├── backend/
│   ├── app/
│   │   ├── ml/               # ML pipeline (training, features, synthetic data)
│   │   ├── models/           # SQLAlchemy models (User, ParkingLot, Zone, Slot, etc.)
│   │   ├── routes/           # API blueprints (auth, lots, slots, insights, camera)
│   │   └── services/         # MQTTService, PredictionService, Notifications
│   ├── docker/
│   ├── migrations/           # Alembic database migrations
│   ├── scripts/              # Data export and training data tooling
│   ├── tests/
│   ├── .env.example
│   ├── docker-compose.realtime.yml
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   └── src/
│       ├── app/              # Next.js pages (dashboard, lots, activity, admin, settings)
│       ├── components/       # Shared UI components
│       ├── hooks/            # Custom React hooks
│       ├── lib/              # API client, formatting, mock data
│       └── types/            # TypeScript interfaces
├── hardware/
│   ├── esp32/
│   ├── simulator/
│   ├── sketches/
│   └── tinkercad/
├── data/
├── docs/
└── ml/
    └── models/               # Trained model artifacts (gitignored)
```

## API Endpoints

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Detailed health status |

### Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Register a new user |
| POST | `/api/v1/auth/login` | Authenticate and receive JWT |
| GET | `/api/v1/auth/me` | Get current user profile |

### Parking Lots

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/lots` | List all parking lots |
| POST | `/api/v1/lots` | Create a parking lot (faculty/admin) |
| GET | `/api/v1/lots/<lot_id>` | Get lot details with slots |
| GET | `/api/v1/lots/summary` | Aggregate statistics across all lots |

### Slots

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/slots` | List slots with optional filters |
| GET | `/api/v1/slots/<slot_id>` | Get a specific slot |
| PUT | `/api/v1/slots/<slot_id>/status` | Update slot status (faculty/admin) |
| PUT | `/api/v1/slots/status/batch` | Batch slot status update (faculty/admin) |
| GET | `/api/v1/slots/<slot_id>/events` | Get recent events for a slot |
| GET | `/api/v1/events` | List events across all slots |

### Predictions and Insights

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/lots/<lot_id>/predict` | ML-backed occupancy prediction by zone |
| GET | `/api/v1/lots/<lot_id>/recommend` | Zone recommendation for a destination |

### Admin (requires admin role)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/sensors` | Sensor fleet health dashboard |
| GET | `/api/v1/admin/analytics` | Historical occupancy analytics |

### Notifications

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/notifications/stream` | SSE stream for live slot-change events |

### Camera Ingest

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/camera/upload` | Camera image upload (token-authenticated) |

## ML Pipeline

PRISM includes a machine learning pipeline for zone-level occupancy prediction.

### Training Data

Training data is assembled from two sources:
- **Synthetic data**: Generated across 4 zones with hourly occupancy curves, day-of-week multipliers, and Gaussian noise (sigma = 4%). Produced by `app.ml.synthetic_data`.
- **Real-world data**: KLCC parking dataset combined via `backend/scripts/combine_training_data.py`.

### Feature Engineering

The pipeline computes 11 features from raw occupancy records (`app.ml.feature_engineering`):
- Temporal: `hour`, `day_of_week`, `is_weekend`
- Cyclical encoding: `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`
- Current state: `current_occupancy_pct`
- Lag features: `lag_1h`, `lag_2h`
- Rolling average: `rolling_avg_3h`

### Model

- Algorithm: `RandomForestRegressor(n_estimators=100, max_depth=15)`
- Evaluation: R-squared = 0.8887, MAE = 4.69%
- Output: `ml/models/occupancy_predictor.pkl` (gitignored)

### Inference

The `PredictionService` is loaded as a Flask extension at startup. When the trained model file is present, the `/api/v1/lots/<lot_id>/predict` endpoint returns ML-backed predictions with `model.status = "active"`. If the model file is missing or fails verification, the service falls back to a rule-based heuristic and returns `model.status = "heuristic_fallback"`.

## MQTT Topic Contract

Topic conventions are documented in [`docs/mqtt_topics.md`](docs/mqtt_topics.md).

- Slot updates: `prism/{lot_id}/slot/{slot_id}` -- JSON with `distance_cm`, `occupied`, `timestamp`
- Heartbeat: `prism/{lot_id}/heartbeat` -- Device health status

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose -f docker-compose.realtime.yml up -d
FLASK_APP=app flask db upgrade
flask seed-campus
python run.py
```

If you want an external simulator or another trusted client to reach Mosquitto, set
`PRISM_MQTT_BIND_ADDRESS` before `docker compose up`. Keep the default `127.0.0.1`
unless you intentionally need remote broker access.

### Train the ML Model

```bash
cd backend
source venv/bin/activate
python -m app.ml.train_model
```

This generates `ml/models/occupancy_predictor.pkl`. The backend will automatically load it on the next restart. Training is optional; the prediction endpoint works without it using the heuristic fallback.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open `http://localhost:3000` to view the dashboard. For live slot activity, run either
the ESP32 firmware or the MQTT simulator so the backend receives slot telemetry.

## Testing

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run all backend tests (realtime tests start/stop Redis + Mosquitto via Docker Compose)
pytest tests/ -v

# Run ML pipeline tests (Day 15)
pytest tests/test_day15_synthetic_data.py tests/test_day15_train_model.py \
       tests/test_day15_prediction_service.py tests/test_day15_predict_endpoint.py -v

# Run non-infrastructure tests only (no Redis/Mosquitto required)
pytest tests/ -q \
  --ignore=tests/test_mqtt_*.py \
  --ignore=tests/test_notifications_redis.py \
  --ignore=tests/test_rate_limits_redis.py \
  --ignore=tests/test_auth_security.py
```

### Frontend E2E Tests

```bash
cd frontend
npm run test:e2e
```

## Environment Variables

Key configuration variables (see `backend/.env.example` for the full list):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Flask secret key | (required) |
| `JWT_SECRET_KEY` | JWT signing key | (required) |
| `DATABASE_URL` | PostgreSQL connection string | (required) |
| `PRISM_REDIS_URL` | Redis URL for notifications and caching | `redis://localhost:6379/0` |
| `PRISM_RATE_LIMIT_STORAGE_URI` | Redis URI for rate limiter backend | `redis://localhost:6379/0` |
| `ML_MODEL_PATH` | Path to trained model pickle file | `../ml/models/occupancy_predictor.pkl` |
| `MQTT_BROKER_HOST` | MQTT broker hostname | `localhost` |
| `MQTT_BROKER_PORT` | MQTT broker port | `1883` |
| `PRISM_MQTT_BIND_ADDRESS` | Mosquitto bind address in Docker | `127.0.0.1` |
| `PRISM_NOTIFICATIONS_BACKEND` | Notification broker type | `redis` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000` |
| `PRISM_AUTO_CREATE_TABLES` | Auto-create tables without migrations (dev only) | `false` |
| `PRISM_ALLOW_PUBLIC_READS` | Allow unauthenticated read access | `false` |
| `LOG_LEVEL` | Application log level | `DEBUG` |

## Branch Policy

- `develop` is the active development branch.
- `main` receives stable, reviewed merges only.
- Feature and experiment work should be isolated in short-lived branches.

## Documentation

- MQTT contract: [`docs/mqtt_topics.md`](docs/mqtt_topics.md)
- API docs: [`docs/api_docs.md`](docs/api_docs.md)
- Hardware assembly guide: [`docs/hardware_assembly_guide.md`](docs/hardware_assembly_guide.md)
- Wiring diagrams: [`docs/wiring_diagram.md`](docs/wiring_diagram.md)
- ML data preparation report: [`docs/day13_ml_data_preparation_report.md`](docs/day13_ml_data_preparation_report.md)
- Day 7 simulation documentation: [`docs/day7_simulation_documentation.md`](docs/day7_simulation_documentation.md)
- Day 7 end-to-end report: [`docs/day7_e2e_simulator_test.md`](docs/day7_e2e_simulator_test.md)
- Day 8-9 assembly checklist: [`docs/day8_day9_physical_assembly_checklist.md`](docs/day8_day9_physical_assembly_checklist.md)
- Day 8 hardware progress update: [`docs/day8_hardware_progress_update.md`](docs/day8_hardware_progress_update.md)
- Day 8 API completion report: [`docs/day8_api_completion_report.md`](docs/day8_api_completion_report.md)
- Phase 1 handoff summary: [`docs/phase1_hardware_simulation_handoff.md`](docs/phase1_hardware_simulation_handoff.md)
