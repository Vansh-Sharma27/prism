# Day 6 Auth + Simulator Enhancement Report

Date: 2026-03-02

## Scope

Day 6 deliverables covered both tracks:

1. Person A (hardware-not-issued path)
- Enhanced simulator with realistic day-part occupancy patterns.
- Added sensor-outage simulation (offline windows).
- Added occupancy-log CSV export tooling for ML dataset preparation.

2. Person B
- Implemented login and register pages with validation.
- Added protected route enforcement for core frontend pages.
- Added admin dashboard skeleton with sensor health table and analytics placeholders.
- Added explicit loading/error/retry UX on polling pages.

## Files Updated

### Simulator/Data (Person A)
- `hardware/simulator/mqtt_simulator.py`
- `hardware/simulator/README.md`
- `backend/scripts/export_occupancy_logs.py`

### Frontend/Auth/Admin (Person B)
- `frontend/src/lib/api.ts`
- `frontend/src/lib/auth-context.tsx`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/components/Navbar.tsx`
- `frontend/src/app/login/page.tsx`
- `frontend/src/app/register/page.tsx`
- `frontend/src/app/admin/page.tsx`
- `frontend/src/app/admin/admin-client.tsx`
- `frontend/src/app/admin/loading.tsx`
- `frontend/src/app/dashboard-client.tsx`
- `frontend/src/app/lots/lots-client.tsx`
- `frontend/src/app/lots/[id]/lot-detail-client.tsx`
- `frontend/src/app/activity/activity-client.tsx`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/hooks/usePolling.ts`
- `frontend/src/app/layout.tsx`

### Security Hardening
- `backend/app/routes/auth.py`
- `backend/app/__init__.py`
- `backend/.env.example`
- `backend/tests/test_auth_security.py`

## Functional Notes

- Protected routes now redirect unauthenticated users to `/login?next=<path>`.
- JWT is stored under `localStorage["prism_access_token"]`.
- Admin route (`/admin`) requires authenticated user role `admin`.
- Register endpoint now blocks privileged self-registration unless explicitly enabled:
  - env: `PRISM_ALLOW_PRIVILEGED_SELF_REGISTER=true`

## Simulator Enhancements

- New simulator mode:
  - `--mode dynamic` (default): follows hourly occupancy profile.
  - `--mode random`: classic random flip behavior.
- Outage simulation:
  - `--failure-probability`
  - `--failure-min-cycles`
  - `--failure-max-cycles`
- Bounded dataset runs:
  - `--cycles`
  - `--seed` for reproducibility.

Example:

```bash
python hardware/simulator/mqtt_simulator.py \
  --mode dynamic \
  --failure-probability 0.03 \
  --cycles 240 \
  --interval 2
```

Dataset export:

```bash
cd backend
python scripts/export_occupancy_logs.py --output ../data/processed/day6_occupancy_logs.csv
```

## Security Notes

- Public self-registration no longer allows role escalation by default.
- Email normalization is enforced during registration (`strip + lower`).
- Privileged self-registration is opt-in via environment configuration.

## Verification Snapshot

- `frontend`: `npm run lint` -> PASS
- `frontend`: `npx tsc --noEmit` -> PASS
- `backend`: `python3 -m pytest -q tests/test_auth_security.py` -> PASS (3 tests)
- `backend`: `python3 -m pytest -q -k "not broker_connection and not publish_subscribe and not slot_update_topic_format and not heartbeat_topic_format"` -> PASS (4 tests; 4 MQTT-network tests deselected)
- `backend`: `python3 -m compileall app scripts run.py` -> PASS
- `simulator`: `python3 hardware/simulator/mqtt_simulator.py --help` -> PASS
- `dataset export`: `python3 backend/scripts/export_occupancy_logs.py --output /tmp/day6_test_export.csv --limit 1` -> PASS

Sandbox limitation:
- Direct socket-level MQTT integration tests are blocked in this environment (`PermissionError: [Errno 1] Operation not permitted`). Those tests should be run on unrestricted local machine/VM where Mosquitto is reachable.
