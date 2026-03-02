# PRISM Frontend

Next.js dashboard for real-time parking slot monitoring. Displays sensor data from ESP32 nodes via the Flask backend API.

## Tech Stack

- **Framework:** Next.js 16 (App Router, TypeScript)
- **Styling:** Tailwind CSS with custom design tokens
- **Fonts:** Barlow Condensed (display), Barlow (body), IBM Plex Mono (data)
- **Icons:** Lucide React

## Project Structure

```
src/
├── app/                  # Next.js App Router pages
│   ├── page.tsx          # Dashboard — stats, lot cards, live slot grid
│   ├── lots/
│   │   ├── page.tsx      # All parking lots
│   │   └── [id]/page.tsx # Lot detail with slot-level view
│   ├── activity/page.tsx # Event log (entries/exits)
│   ├── settings/page.tsx # System configuration display
│   ├── globals.css       # Design tokens and utility classes
│   └── layout.tsx        # Root layout with fonts and metadata
├── components/           # Shared UI components
│   ├── Navbar.tsx         # Navigation bar with system clock
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

If backend read endpoints require auth, set either:

```bash
# Option 1: env token for all browser sessions
NEXT_PUBLIC_API_TOKEN=<jwt_token>
```

Or in browser devtools:

```js
localStorage.setItem("prism_access_token", "<jwt_token>")
```

The `src/lib/api.ts` file provides live API adapters (`fetchDashboardData`, `fetchLotDetailData`, `fetchActivityEvents`) consumed by dashboard, lots, lot-detail, and activity pages.
