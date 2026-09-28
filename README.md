# Transfer Index

Transfer Index is a football scouting and transfer intelligence platform that combines player profiles, season performance, advanced statistics, market-value history, transfer records, and club context to evaluate both player quality and potential transfer fit.

**Development Status:** Active Development

## Overview

Football recruitment decisions depend on more than a player's headline statistics. Transfer Index brings several parts of the scouting workflow into one application:

- player profiles and current-club information;
- season performance and position-relevant advanced metrics;
- historical market valuations and career transfers;
- server-side scouting search and filtering;
- club squad, age, nationality, footedness, and financial summaries;
- deterministic player scoring and target-club transfer analysis.

The project separates two related but different questions:

1. **Player evaluation:** How strong is the player independently of a destination club?
2. **Player → target club fit:** How suitable is that player for a specific club's squad and financial context?

## Key Features

### Player Database

- Searchable and paginated player records
- Player name, age, nationality, position, preferred foot, club, and league
- Current market value, contract data, physical profile, and season output where available
- Dedicated player and club pages
- Side-by-side player comparison
- Similar-player suggestions based on profile and performance attributes

### Player Analytics

- Appearances, starts, minutes, goals, assists, and per-90 production
- Position-aware advanced statistics for strikers, wingers, midfielders, defensive midfielders, centre-backs, full-backs, and goalkeepers
- Club-independent deterministic player score with quality grade, strengths, and risks
- Missing optional data remains visible as unavailable instead of removing the player from the database

### Market Value Intelligence

- Current and peak market value
- Lowest recorded value and historical growth calculation
- Historical valuation chart on the player page

### Career Transfer History

- Previous and destination clubs
- Transfer date and season
- Market value and transfer fee
- Transfer type, including loans, loan returns, and free transfers when present in the source data

### Scouting Database

The scouting page performs filtering on the server and supports combined filters for:

- player search;
- position;
- nationality;
- league;
- club;
- preferred foot;
- minimum and maximum age;
- minimum and maximum market value;
- minimum minutes;
- minimum goals;
- minimum assists.

Search input is debounced, numeric ranges are validated, filter options are derived from database values, and resetting the filters restores the default player list.

### Transfer Scenario Analyzer

```text
Player + Target Club
          ↓
Deterministic Transfer Fit Analysis
```

The analyzer combines the selected player's structured context with the destination club's squad composition and financial profile. Selecting the player's current club is rejected by backend validation.

### Deterministic Transfer Fit Engine

The Transfer Fit Score is calculated by application logic, not by a language model. The current factors and weights are:

| Factor | Weight |
| --- | ---: |
| Player Quality | 20% |
| Squad Fit | 15% |
| Financial Fit | 15% |
| Performance | 15% |
| Advanced Stats | 10% |
| Age Profile | 8% |
| Contract | 7% |
| Culture Fit | 5% |
| Pressure Readiness | 3% |
| Transfer Risk | 2% |

`transfer_risk_score` represents risk severity, so its contribution is inverted in the final fit calculation. If a sub-score cannot be calculated from verified data, it remains `null`; the final score is normalized over the weights of the available sub-scores instead of treating missing data as zero.

Grades use these ranges:

| Score | Grade |
| --- | --- |
| 85–100 | Elite Fit |
| 70–84 | Strong Fit |
| 55–69 | Moderate Fit |
| 40–54 | Risky Fit |
| 0–39 | Poor Fit |

### AI Scout Analysis — Planned / In Development

The Transfer Scenario OpenAI provider is not currently enabled. The implemented preparation layer is:

```text
Deterministic Engine
        ↓
Compact Context Builder
        ↓
Stable JSON + SHA256 Context Hash
        ↓
7-Day Cache Lookup
        ↓
AI Interpretation (planned)
```

On a cache miss, the current endpoint returns `source: "fallback"` with the deterministic result and does not call OpenAI or cache the fallback. The intended AI layer will interpret the structured analysis; it will not invent or replace the Transfer Fit Score.

The repository also contains a separate OpenRouter-based player-report route. That legacy report is independent of the deterministic Transfer Scenario AI architecture.

## Data Sources

### Transfermarkt-derived CSV data

Import scripts support player metadata, clubs, competitions, appearances, market valuations, and transfer history from CSV files using Transfermarkt-style schemas.

### FBref-derived advanced statistics

The advanced-stat import supports 2024/25 player metrics such as expected goals, expected assists, shots, progression, chance creation, defensive actions, aerials, and available goalkeeper statistics.

Transfer Index is an independent educational and portfolio project. It is not affiliated with Transfermarkt or FBref. Data ownership and usage rights remain with the respective providers and dataset owners. The repository ignores the primary Transfermarkt CSV directory; obtain and use datasets in accordance with their applicable terms.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL, Pandas, Pydantic |
| Frontend | React, Vite, Tailwind CSS, React Router, Recharts |
| AI status | OpenAI API for Transfer Scenario interpretation — planned/in development |
| Optional legacy AI | OpenRouter-compatible player report service through the OpenAI Python client |
| Testing | Python `unittest`, FastAPI `TestClient` |

## Architecture

```mermaid
flowchart LR
    UI[React / Vite Frontend] -->|HTTP JSON| API[FastAPI API]
    API --> SERVICES[Context and Analysis Services]
    SERVICES --> DB[(PostgreSQL)]
    IMPORTS[CSV Import Scripts] --> DB
    TM[Transfermarkt-derived Data] --> IMPORTS
    FB[FBref-derived Data] --> IMPORTS
```

```mermaid
flowchart TD
    PLAYER[Player Context] --> ENGINE[Deterministic Transfer Fit Engine]
    CLUB[Target Club Context] --> ENGINE
    ENGINE --> SCORE[Fit Score, Sub-scores, Strengths, Risks]
    SCORE --> COMPACT[Compact AI Context and SHA256 Hash]
    COMPACT --> FALLBACK[Deterministic Fallback]
    COMPACT -. planned .-> AI[AI Interpretation]
```

## Project Structure

```text
transfer-index/
├── backend/
│   ├── .env.example
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── data/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── scripts/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── database.py
│   │   └── main.py
│   └── tests/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── assets/
│   │   ├── pages/
│   │   │   ├── ClubPage.jsx
│   │   │   ├── ComparePage.jsx
│   │   │   ├── Home.jsx
│   │   │   ├── PlayerPage.jsx
│   │   │   └── Scouting.jsx
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Node.js compatible with Vite 8
- PostgreSQL

### Backend Setup

The repository currently has no committed `requirements.txt` or `pyproject.toml`. Install the backend packages used by the code explicitly:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install fastapi "uvicorn[standard]" sqlalchemy psycopg2-binary pandas python-dotenv pydantic openai
```

For macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

Copy `backend/.env.example` to `backend/.env`, then configure the server environment. Never commit `.env`.

### Database Configuration

The backend reads the PostgreSQL connection from `DATABASE_URL`:

```dotenv
DATABASE_URL=postgresql://username:password@localhost:5432/transfer_index
```

Create the database before starting the API. The current application calls SQLAlchemy `Base.metadata.create_all()` during startup; no migration framework is included yet.

Initialize the mapped tables without starting a long-running server:

```powershell
python -c "import app.main"
```

### Dataset Import

Run import commands from the `backend/` directory. The scripts expect these user-supplied files:

```text
app/data/transfermarkt/players.csv
app/data/transfermarkt/national_teams.csv
app/data/transfermarkt/clubs.csv
app/data/transfermarkt/competitions.csv
app/data/transfermarkt/appearances.csv
app/data/transfermarkt/games.csv
app/data/transfermarkt/player_valuations.csv
app/data/transfermarkt/transfers.csv
app/data/fbref_player_stats.csv
```

A practical import order is:

```powershell
python -m app.scripts.import_transfermarkt
python -m app.scripts.import_clubs
python -m app.scripts.import_player_club_ids
python -m app.scripts.import_player_stats
python -m app.scripts.import_player_valuations
python -m app.scripts.import_transfers
python -m app.scripts.import_fbref_advanced_stats
```

The import scripts validate required columns and report skipped or unmatched rows. Review the scripts before running them against an existing database because some importers replace the corresponding historical records.

### Run the Backend

From `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The API is then available at `http://127.0.0.1:8000`, with interactive documentation at `http://127.0.0.1:8000/docs`.

### Frontend Setup

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173` in a browser. The development CORS configuration also permits `http://localhost:5173`.

### Tests

From `backend/`:

```powershell
python -m unittest discover -s tests -v
```

Build and lint the frontend from `frontend/`:

```powershell
npm run build
npm run lint
```

## Environment Variables

| Variable | Status | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Required | PostgreSQL SQLAlchemy connection string |
| `OPENROUTER_API_KEY` | Used by the legacy AI report service | Authenticates requests made by `AIScoutService` |
| `OPENROUTER_MODEL` | Optional | Overrides the legacy OpenRouter model; defaults to `openai/gpt-3.5-turbo` |
| `OPENAI_API_KEY` | Reserved / not currently consumed | Present as a placeholder for the planned Transfer Scenario OpenAI provider |

API credentials belong only in the backend environment. Do not expose them through Vite variables, frontend code, or source control.

## API Overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/players/search` | Paginated player search and combined scouting filters |
| `GET` | `/players/filter-options` | Database-derived filter values |
| `GET` | `/players/{player_id}` | Player profile |
| `GET` | `/players/{player_id}/player-score` | Club-independent deterministic player score |
| `GET` | `/players/{player_id}/advanced-stats` | Season advanced statistics |
| `GET` | `/players/{player_id}/valuations` | Market-value summary and history |
| `GET` | `/players/{player_id}/transfers` | Career transfer history |
| `GET` | `/players/compare` | Two-player comparison |
| `GET` | `/clubs/search` | Target-club search with current-club exclusion support |
| `GET` | `/clubs/{club_name}/context` | Structured club intelligence context |
| `POST` | `/transfer-scenarios/analyze` | Deterministic player-to-club transfer analysis |
| `POST` | `/transfer-scenarios/ai-analyze` | Cache lookup and deterministic fallback; external provider currently disabled |

## Transfer Fit Philosophy

Player quality and transfer fit are not interchangeable. A high-quality player may still be a poor target for a club with strong depth in the same position, limited financial capacity, an incompatible age profile, or a difficult contract situation. Transfer Index keeps the player-quality assessment separate, then evaluates squad need, financial context, age, contract, performance, advanced metrics, and objective adaptation signals for the selected destination.

## Responsible AI & Data Limitations

- AI interpretation must remain grounded in the supplied structured context and deterministic analysis.
- The system should not invent private-life, personality, tactical, medical, or dressing-room claims.
- Missing information is represented as unavailable rather than guessed or scored as zero quality.
- Transfer Fit is analytical decision support, not a guarantee of transfer completion or future performance.
- Dataset coverage, matching quality, and freshness directly affect results.
- Financial fit currently uses available market-value context; it is not a verified club transfer budget or wage model.

## Roadmap

- [x] Player database and player detail pages
- [x] Club pages and player comparison
- [x] Market-value history and career transfer history
- [x] Season performance and advanced-stat views
- [x] Server-side scouting search and combined filters
- [x] Club context and squad-profile builder
- [x] Transfer Scenario modal and target-club validation
- [x] Deterministic Transfer Fit engine
- [x] Compact AI context, stable hashing, and seven-day cache infrastructure
- [x] Backend regression tests for deterministic scoring and AI infrastructure
- [ ] Enable the Transfer Scenario OpenAI interpretation provider
- [ ] Add a committed Python dependency manifest
- [ ] Add database migrations and deployment configuration
- [ ] Expand data-quality, API, and frontend end-to-end coverage
- [ ] Continue club/logo and dataset enrichment where source data permits

## Screenshots

### Player Profile

<!-- Add screenshot -->

### Scouting Database

<!-- Add screenshot -->

### Transfer Scenario Analyzer

<!-- Add screenshot -->

## Disclaimer

Transfer Index is an independent educational and portfolio project. It is not affiliated with Transfermarkt, FBref, football clubs, or football leagues. Data belongs to its respective providers and owners.

## Author

Baran Doğrular
