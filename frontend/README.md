# PRISM Frontend

Next.js dashboard for real-time parking slot monitoring. Displays sensor data from ESP32 nodes via the Flask backend API.

## Tech Stack

- **Framework:** Next.js 16 (App Router, TypeScript)
- **Styling:** Tailwind CSS with custom design tokens
- **Fonts:** Barlow Condensed (display), Barlow (body), IBM Plex Mono (data) vendored locally for offline-safe builds
- **Icons:** Lucide React

## Project Structure

```
src/
├── app/                  # Next.js App Router pages
│   ├── page.tsx          # Dashboard — stats, lot cards, live slot grid
│   ├── login/page.tsx    # Login form (validation + redirect)
│   ├── register/page.tsx # Registration form (validation + auto-login)
│   ├── lots/
│   │   ├── page.tsx      # All parking lots
│   │   └── [id]/page.tsx # Lot detail with slot-level view
│   ├── activity/page.tsx # Event log (entries/exits)
│   ├── admin/page.tsx    # Admin skeleton (sensor health + chart placeholders)
│   ├── settings/page.tsx # System configuration display
│   ├── globals.css       # Design tokens and utility classes
│   └── layout.tsx        # Root layout with fonts and metadata
├── components/           # Shared UI components
│   ├── Navbar.tsx         # Navigation bar with system clock
│   ├── ProtectedRoute.tsx # Auth + role gate for protected pages
│   ├── StatsGrid.tsx      # System status bar with progress indicator
│   ├── LotCard.tsx        # Parking lot summary card
│   ├── SlotCard.tsx       # Individual slot status card
│   ├── SlotGrid.tsx       # Color-coded slot matrix for lot detail
│   ├── PageHeader.tsx     # Shared page/section headers and StatCell
│   ├── Skeleton.tsx       # Loading skeleton components
│   └── EmptyState.tsx     # Empty state display
├── hooks/
│   └── usePolling.ts      # Shared auto-refresh polling hook
├── lib/
│   ├── api.ts            # Live API adapters + auth-token aware fetch wrapper
│   ├── auth-context.tsx  # Auth provider and session lifecycle
│   ├── format.ts         # Date/time formatting utilities
│   └── mock-data.ts      # Mock data for development
└── types/
    └── parking.ts        # TypeScript interfaces
```

## Development

```bash
npm install
npm run dev
```

The dev server starts at `http://localhost:3000`. To expose on the network:

```bash
npx next dev --hostname 0.0.0.0
```

## Build

```bash
npm run build
npm start
```

## Hydration Guard

Hydration mismatches happen when server HTML and the first client render differ.

Guard rules used in this codebase:

1. Keep first render deterministic (no `Date.now()`, `Math.random()`, or `window/localStorage` branching in initial render output).
2. Move browser-only state resolution into `useEffect`.
3. Use `suppressHydrationWarning` only at root boundaries where external attribute mutations (for example browser extensions) can occur.
4. Add automated console checks so hydration warnings fail tests early.

Run the hydration console guard:

```bash
npm run test:e2e:hydration
```

The test fails if routes emit hydration mismatch console warnings/errors (for example `Hydration failed` or `server rendered HTML didn't match client`).

## Auth E2E Coverage

Expanded auth behavior tests now cover:

- protected-route redirect with preserved `next` query
- login validation failures and invalid-credential server errors
- open-redirect protection on `next`
- register validation and duplicate-email conflict
- successful student registration flow + admin-role denial
- forced logout on unauthorized protected API responses

Run the auth suite:

```bash
npm run test:e2e:auth
```

Run full Playwright suite:

```bash
npm run test:e2e
```

## Design System

The interface uses an industrial control-room aesthetic. Design tokens are defined as CSS custom properties in `globals.css`:

- **Status colors:** `--vacant` (green), `--occupied` (red), `--offline` (gray), `--warning` (amber)
- **Surfaces:** Four background tiers (`--bg-primary` through `--bg-elevated`)
- **Accent:** Industrial amber (`--accent`) used for interactive elements and highlights

Utility classes: `.card-industrial`, `.card-primary`, `.card-secondary`, `.status-dot-*`, `.font-display`, `.label-quiet`, `.divider-accent`, `.skeleton`

## Connecting to the Backend

Set API and proxy values in `.env.local`:

```
NEXT_PUBLIC_API_URL=/api/v1
PRISM_BACKEND_URL=http://127.0.0.1:5000
```

The frontend now includes Day 6 auth pages:

- `GET /login`
- `GET /register`

Successful login stores JWT in `localStorage["prism_access_token"]`. Protected pages (`/`, `/lots`, `/lots/[id]`, `/activity`, `/settings`, `/admin`) enforce client-side auth via `ProtectedRoute`.

If backend read endpoints require auth and you want to bypass login UI in local testing, set either:

```bash
# Option 1: env token for all browser sessions
NEXT_PUBLIC_API_TOKEN=<jwt_token>
```

Or in browser devtools:

```js
localStorage.setItem("prism_access_token", "<jwt_token>")
```

The `src/lib/api.ts` file provides live API adapters (`fetchDashboardData`, `fetchLotDetailData`, `fetchActivityEvents`) consumed by dashboard, lots, lot-detail, and activity pages.
