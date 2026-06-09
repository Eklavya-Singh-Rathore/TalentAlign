# TalentAlign — Frontend

Next.js dashboard for the TalentAlign career intelligence platform. Renders
the 29-key analysis payload from the [backend](../backend) across six screens:
Upload & Match, Match Overview, Component Alignment, Gap Analysis,
Recommendations, and Report & Export.

## Stack

- Next.js 14 (App Router) · React 18 · TypeScript 5
- Tailwind CSS 3
- Framer Motion (page transitions)
- Recharts (component bar / radar / radial)
- Lucide React (icons)
- `clsx` + `tailwind-merge` for the `cn()` utility
- localStorage for analysis history (max 20 items)

## Layout

```
src/
├── app/                      App-router pages (/, /analysis, /reports, /settings)
├── components/
│   ├── layout/               Shell, sidebar, header
│   ├── upload/               Resume dropzone, JD input, validation banner
│   ├── dashboard/            Score gauge, KPI cards, component breakdown,
│   │                         gap analysis, recommendations, report export,
│   │                         Candidate Assessment (LLM-only)
│   ├── charts/               Bar / radar / radial / skill-match
│   ├── tables/               Matched skills, analysis history
│   └── ui/                   Button, card, badge, empty-state, tabs
├── lib/                      API client, types, formatters, validators
├── hooks/                    useUpload, useAnalysis, useResponsive
└── stores/                   AnalysisProvider (Context + localStorage)
```

## Environment variables

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend `/health` + `/analyze` origin (default `http://localhost:8000`) |

Copy [`.env.example`](.env.example) to `.env.local` and adjust for your setup.

## Running locally

```bash
# Install deps
npm install

# Dev server (http://localhost:3000)
npm run dev

# Type check
npx tsc --noEmit

# Production build
npm run build
npm start
```

Make sure the backend is running at `NEXT_PUBLIC_API_BASE_URL` (default
`http://localhost:8000`) — the dashboard hits it for every analysis.

## Deployment (Vercel)

A [`vercel.json`](vercel.json) is included with the standard Next.js
preset. Configure these on the Vercel project:

| Setting | Value |
|---------|-------|
| Framework preset | Next.js |
| Build command | `next build` (from `vercel.json`) |
| Install command | `npm install` |
| Output directory | `.next` |
| `NEXT_PUBLIC_API_BASE_URL` | Production backend origin |

Then add the same Vercel deployment URL (and any preview-deployment
wildcard, e.g. `https://*.vercel.app`) to the backend's
`TALENTALIGN_CORS_ORIGINS` so the dashboard can reach the API.

## Candidate Assessment card

The narrative card (LLM-generated overall evaluation, strengths, gaps,
hiring recommendation) is conditionally rendered based on
`analysis.debug.llm_backend !== "none"` or
`analysis.explainability.llm_polishing_used`. When the backend runs in
deterministic-only mode (no Gemini key), the card is hidden and only the
component-derived data is shown.
