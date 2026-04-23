# Agility Sprint Dashboard

Sprint-wise **planned vs delivered** story metrics for FedEx SCO P&D teams in Agility VersionOne â€” served via FastAPI with browser-based OKTA/SSO login and an interactive Plotly dashboard.

---

## Features

- **ART-filtered team selection** â€” three Agile Release Trains (Conveyence, Plan N Prepare, Run and Close) with per-ART team dropdowns
- **Sprint Velocity chart** â€” planned vs delivered stories per sprint for the selected team
- **Story Points chart** â€” planned vs delivered points per sprint
- **Delivery Rate chart** â€” sprint completion % over time
- **Committed vs Completed by ART** â€” lazy-loaded tab showing all-time totals across all 3 ARTs
- **Team Performance by ART** â€” lazy-loaded tab showing per-team committed/completed for the selected ART
- **5-minute response cache** â€” team list and story counts cached in memory; switching teams/ARTs is near-instant after first load
- **Date range filter** â€” restrict charts and tables to a custom sprint window

---

## Architecture

```
Browser (static/index.html)
        |
        | POST /login/start  â†’  OKTA browser window  â†’  cookies
        |
        | GET  /arts                    (instant â€” from config.py)
        | GET  /teams?art=<ART>         (Agility API â€” ~5s first time, cached)
        | GET  /teams/{oid}/summary     (Agility API â€” cached per team)
        | GET  /art-performance         (lightweight counts â€” cached 5 min)
        | GET  /art-teams-performance   (lightweight counts â€” cached 5 min)
        v
+----------------------------------------------------------+
|                   FastAPI  (main.py)                     |
|                                                          |
|  Auth                                                    |
|    POST /login/start        â€“ OKTA Selenium browser     |
|    GET  /login/status       â€“ check active session      |
|    DELETE /login/clear      â€“ sign out                  |
|                                                          |
|  Teams & ARTs                                            |
|    GET  /teams              â€“ teams filtered by ?art=   |
|    GET  /arts               â€“ ART names from config     |
|    GET  /debug/teams        â€“ diagnostic: all teams     |
|                                                          |
|  Dashboard                                               |
|    GET  /teams/{oid}/summary       â€“ per-team sprints   |
|    GET  /art-performance           â€“ ART-level totals   |
|    GET  /art-teams-performance     â€“ team-level totals  |
|    GET  /cache/clear               â€“ flush cache        |
|                                                          |
|  Utility                                                 |
|    GET  /health             â€“ liveness probe            |
+-----------------------------+----------------------------+
                              |
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          v                                       v
+----------------------+             +------------------------+
|  auth_browser.py     |             |  agility_client.py     |
|  (Selenium)          |             |  (httpx async)         |
|                      |             |                        |
|  Launches browser,   |             |  Cookie-auth against   |
|  auto-fills OKTA,    |             |  VersionOne REST API   |
|  captures cookies,   |             |  /Team /Timebox /Story |
|  saves to            |             +------------------------+
|  .auth_session.json  |
+----------------------+
```

---

## Quick Start

### 1. Clone / open the project

```powershell
cd C:\AgilityAutomation
```

### 2. Configure environment

Create a `.env` file (or edit the existing one):

```env
AGILITY_BASE_URL=https://www19.v1host.com/FedEx
TEAM_ROOM_OID=TeamRoom:15671286
```

> `AGILITY_USERNAME` and `AGILITY_PASSWORD` are **not** required â€” authentication is handled entirely through the OKTA browser window at login time.

### 3. Start the server

```powershell
.\start.ps1
```

The script will:
1. Create a `.venv` virtual environment if one does not exist
2. Install all dependencies from `requirements.txt`
3. Start the FastAPI server on **http://localhost:8001**

Or start manually:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Open the dashboard

Navigate to **http://localhost:8001**

Swagger API docs: **http://localhost:8001/docs**

---

## Login Flow

FedEx uses OKTA/SSO â€” direct API authentication is not supported. The app authenticates via a real browser session:

1. Open **http://localhost:8001**
2. Enter your FedEx username and password
3. A Chrome/Edge browser window opens and auto-fills your credentials
4. Complete MFA (push notification or OTP) in the browser
5. The window closes automatically once authenticated
6. Session cookies are saved to `.auth_session.json` (valid for ~8 hours)
7. The dashboard loads automatically

---

## API Endpoints

### Auth

```http
POST   /login/start     # Open OKTA browser login
GET    /login/status    # Check if session is active
DELETE /login/clear     # Sign out and clear cookies
```

### Teams & ARTs

```http
GET /arts                         # List ART names (instant â€” no API call)
GET /teams?art=SCO+-+P%26D+-+...  # Teams for a given ART (cached)
GET /debug/teams                  # Diagnostic: all teams with ART matching info
```

### Dashboard

```http
GET /teams/{team_oid}/summary?year=2026   # Sprint-wise summary for one team
GET /art-performance                       # All-time committed/completed per ART
GET /art-teams-performance?art=<name>     # All-time committed/completed per team
GET /cache/clear                           # Flush in-memory cache (forces fresh fetch)
```

### Utility

```http
GET /health    # Liveness probe â†’ {"status": "ok"}
```

---

## ART â†’ Team Mapping

Teams are mapped to their ART in `config.py` via `ART_TEAM_MAP` â€” a dict of exact Agility team names keyed by ART name. Lookup is Unicode-normalised and case-insensitive.

| ART | Teams |
|---|---|
| SCO - P&D - Conveyence | 22 teams (CONV, Conveyance prefix) |
| SCO - P&D - Plan N Prepare | 23 teams (PPO, Plan & Prepare prefix) |
| SCO - P&D - Run and Close | 27 teams (R&C, Run and Close prefix) |

To add a team: append its **exact Agility name** to the appropriate list in `ART_TEAM_MAP`.  
To check which names are unmatched: `GET /debug/teams`.

---

## Response Shape â€“ `/teams/{oid}/summary`

```json
{
  "team_oid": "Team:12345",
  "team_name": "SCO - P&D - R&C - BackBenchers",
  "sprints": [
    {
      "sprint_oid": "Timebox:67890",
      "sprint_name": "Sprint 1",
      "begin_date": "2026-01-06",
      "end_date": "2026-01-17",
      "total_planned": 12,
      "total_delivered": 9,
      "planned_points": 34.0,
      "delivered_points": 28.5
    }
  ]
}
```

## Response Shape â€“ `/art-performance`

```json
[
  { "art": "SCO - P&D - Conveyence",     "committed": 445, "completed": 539 },
  { "art": "SCO - P&D - Plan N Prepare", "committed": 618, "completed": 704 },
  { "art": "SCO - P&D - Run and Close",  "committed": 1146, "completed": 1133 }
]
```

---

## Performance

| Action | API calls | Notes |
|---|---|---|
| Initial load (ART names) | **0** | Served from `config.py` |
| ART selection (27 teams) | **1** | Team list, cached 5 min |
| Team detail (first visit) | **2** | Sprints + stories, cached 5 min |
| Team detail (cached) | **0** | Instant cache hit |
| ðŸ“Š ART overview chart | **72** | One `Status.Name`-only query per team |
| ðŸ“Š ART teams chart | **27** | One `Status.Name`-only query per ART team |
| After `GET /cache/clear` | Fresh | All caches flushed |

---

## Project Structure

```
AgilityAutomation/
â”œâ”€â”€ main.py               â€“ FastAPI app & all endpoints
â”œâ”€â”€ agility_client.py     â€“ VersionOne REST API client (cookie auth)
â”œâ”€â”€ auth_browser.py       â€“ Selenium OKTA browser login
â”œâ”€â”€ models.py             â€“ Pydantic data models
â”œâ”€â”€ config.py             â€“ ART_TEAM_MAP, env vars, normalisation helpers
â”œâ”€â”€ graph_utils.py        â€“ (legacy) Plotly server-side chart builder
â”œâ”€â”€ static/
â”‚   â””â”€â”€ index.html        â€“ Single-page dashboard UI (vanilla JS + Plotly)
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .env                  â€“ AGILITY_BASE_URL, TEAM_ROOM_OID
â”œâ”€â”€ start.ps1             â€“ One-click server startup script
â””â”€â”€ README.md
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | API framework |
| `uvicorn` | ASGI server |
| `httpx` | Async HTTP client for Agility API |
| `pydantic` | Data validation / models |
| `python-dotenv` | `.env` file loading |
| `selenium` + `webdriver-manager` | OKTA browser login |
| `plotly` | Client-side interactive charts |
