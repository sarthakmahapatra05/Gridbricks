   # Wind Forecast Reliability — Day-Ahead Buying

An executive decision-support analytics web application tailored for a UK electricity utility procuring power in the day-ahead wholesale electricity market.

Day-ahead wholesale purchase decisions are locked in on day $D-1$ before gate closure (default 09:00 UK Time). To balance supply commitments and avoid punitive imbalance settlement charges, energy traders must benchmark National Grid ESO wind forecasts against settled actual generation outturn.

---

## Live Links (Submission)

- **Frontend (Vercel):** `https://<YOUR-VERCEL-APP-NAME>.vercel.app` *(Placeholder — follow deployment instructions below)*
- **Backend API (Render):** `https://<YOUR-RENDER-APP-NAME>.onrender.com` *(Placeholder — follow deployment instructions below)*
- **Interactive API Documentation:** `https://<YOUR-RENDER-APP-NAME>.onrender.com/docs`
- **Video Walkthrough Demo:** `https://youtu.be/<YOUR_VIDEO_ID>` *(10-minute unlisted YouTube video)*

---

## Data Source & API Specification

Data is ingested directly from the official **Elexon BMRS API** (`https://data.elexon.co.uk/bmrs/api/v1`):

### 1. Actual Outturn Generation (`FUELHH` Stream)
- **Endpoint:** `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH/stream`
- **Filter:** `fuelType=WIND`
- **Parameters:** `settlementDateFrom=2025-12-31&settlementDateTo=2026-01-31&fuelType=WIND`
- **Cadence:** Half-hourly (48 settlement periods per delivery day).

### 2. Wind Generation Forecast (`WINDFOR` Stream)
- **Endpoint:** `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR/stream`
- **Parameters:** `publishDateTimeFrom=2025-12-31T00:00:00Z&publishDateTimeTo=2026-01-31T23:59:59Z`
- **Cadence:** Hourly (:00 slots). Multiple forecast revisions published throughout day $D-1$ and $D$.

---

## Decision Logic & Operational Rules

1. **Anti-Lookahead Decision Cutoff Rule**:
   - For delivery day $D$, the buyer decides on day $D-1$ at cutoff hour (default **09:00 UK Time**, Europe/London).
   - For every target `startTime` on day $D$, the system strictly filters for the forecast revision with the latest `publishTime <= cutoff`.
   - Forecasts published after the cutoff time are strictly excluded to avoid lookahead bias.

2. **Resolution & Alignment**:
   - `FUELHH` reports half-hourly (48 periods/day), whereas `WINDFOR` forecasts are hourly (24 periods/day).
   - Unforecasted `:30` half-hour slots are maintained as clean gaps (`connectNulls={false}`). No synthetic linear interpolation is performed.
   - All statistical metrics (MAE, RMSE, Bias, Bias %) are evaluated strictly on the 24 hourly aligned points per day (744 total points for January 2026).

3. **Key Findings & Bias Diagnostics**:
   - **January Benchmark:** Mean Forecast = 13,433 MW | Mean Actual = 11,581 MW.
   - **Systemic Bias:** +1,852 MW (+16.0% relative to actual outturn) with $r = 0.9283$ correlation.
   - **Timestamp Shift Check:** Evaluated shifts from -2h to +2h; peak correlation occurs at +0.0h to +0.5h ($r = 0.9283$ vs $0.9287$), confirming that the bias is not caused by timezone misalignment (UTC vs GMT/BST), but is structural.
   - **Thermal Buffer Recommendation:** Based on January's error, hold a base reserve buffer of ~1,852 MW and up to 5,329 MW on peak-error days (e.g. Jan 28).

---

## Modern Sidebar UI/UX Architecture

The interface is crafted for executive power traders who require high accessibility, swift operational controls, and deep empirical evidence:

- **Left Control & Filter Sidebar (Desktop):**
  - Fixed `280px` wide navigation and filtering rail on desktop.
  - **Delivery Date**: Stepper buttons (`◀` / `▶`) paired with a styled date dropdown.
  - **Decision Cutoff**: Dropdown with instant feedback (*"Latest forecast locked before cutoff on D-1"*).
  - **Trading Scenarios**: Vertical stack of 1-click presets (*Lowest Wind*, *Mid-Month*, *Average Day*, *Windiest Day*, *Biggest Miss*).
  - **View Navigation**: 1-click jump links with live scroll-spy tracking.
  - **Status Badge**: Real-time Elexon BMRS API indicator.

- **Increased Vertical Rhythm & Chart Heights:**
  - Natural, generous vertical breathing room (`padding: 64px 48px`).
  - Settlement delivery timeline chart expanded to `440px` height (min `380px`), providing ample room for 48 half-hour intervals without visual compression.
  - 31-day benchmark bar chart expanded to `380px` height.

- **Refined Heading Styling:**
  - Removed the long em-dash (`—`), replacing it with an elegant title: `Actual vs. Decision Forecast · 15 Jan 2026`.

- **Minimal Aesthetic Footer:**
  - Clean 3-column layout at the base of the page detailing official Elexon ingestion streams (`FUELHH` and `WINDFOR`), trading architecture rules (Day D-1 anti-lookahead cutoff), and an animated live verification status pill (*"All 744 January Settlement Hours Verified"*).

- **Flawless Mobile Experience:**
  - Sticky top header featuring the brand, quick date stepper (`◀ 15 Jan ▶`), and a dedicated `Filters` button.
  - Smooth slide-out off-canvas drawer with backdrop blur.
  - Dynamically spaced tick marks (`minTickGap`) eliminating label collision on compact screens.

---

## Directory & File Structure

```text
Gridbricks/
├── backend/
│   ├── data/
│   │   ├── actual_wind.csv          # 1,536 half-hourly actuals (Dec 31, 2025 - Jan 31, 2026)
│   │   └── forecast_wind.csv        # 18,688 forecast records published during the period
│   ├── tests/
│   │   ├── test_analysis.py         # Unit tests for anti-lookahead rules and metrics
│   │   └── test_api.py              # Integration tests for FastAPI endpoints
│   ├── analysis.py                  # Core forecast selection and statistical evaluation
│   ├── diagnostic.py                # Diagnostic script for bias persistence and ratio
│   ├── fetch_data.py                # Ingestion script targeting official Elexon BMRS API
│   ├── main.py                      # FastAPI web server and CORS middleware
│   ├── requirements.txt             # Python dependencies (fastapi, uvicorn, pandas, pytest)
│   ├── time_shift_check.py          # Timestamp shift correlation check (-2h to +2h)
│   ├── .dockerignore
│   └── Dockerfile                   # Multi-platform Python 3.11 slim image
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Single-page dashboard (Charts, KPIs, Buffer Guidance)
│   │   ├── index.css                # Standard 1440px desktop design system
│   │   └── main.jsx                 # React entry point
│   ├── index.html                   # HTML template with Google Fonts (Inter)
│   ├── nginx.conf                   # Nginx reverse proxy & static file server
│   ├── package.json                 # Vite + React 19 + Recharts dependencies
│   ├── vercel.json                  # Single-page app rewrite configuration for Vercel
│   ├── vite.config.js               # Vite bundler configuration
│   ├── .dockerignore
│   └── Dockerfile                   # Multi-stage build (Node 20 build -> Nginx Alpine serve)
├── docker-compose.yml               # Multi-container orchestration (ports 3000 & 8000)
├── render.yaml                      # Render Infrastructure-as-Code blueprint
├── vercel.json                      # Root Vercel project configuration
├── screenshot.png                   # Full-page screenshot of the dashboard
├── .gitignore
└── README.md                        # Documentation and deployment guide
```

---

## How to Run Locally

### Option 1: Docker Compose (Recommended)

Make sure Docker Desktop is running, then run:

```bash
docker compose up --build
```

- **Frontend Dashboard:** [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

To stop the containers:
```bash
docker compose down
```

---

### Option 2: Running Without Docker

#### 1. Backend (Python 3.10+)

```bash
# Navigate to project root
cd Gridbricks

# Install Python dependencies
pip install -r backend/requirements.txt

# Run unit and API test suite (10/10 tests)
python -m pytest backend/tests -v

# Start FastAPI server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

#### 2. Frontend (Node.js 18+)

```bash
# In a new terminal tab:
cd Gridbricks/frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Step-by-Step Deployment Instructions

### Part 1: Push Project to GitHub

1. Create a **public** repository on GitHub with an anonymous name (e.g. `kjhwr-wind-forecast`).
2. Push this project code:
   ```bash
   git init
   git add .
   git commit -m "Complete UK Day-Ahead Wind Forecasting & Decision Support Application"
   git branch -M main
   git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO_NAME>.git
   git push -u origin main
   ```

---

### Part 2: Deploy Backend to Render (Free Web Service)

1. Sign up or log into [Render.com](https://render.com).
2. Click **New +** > **Web Service**.
3. Connect your GitHub repository (`kjhwr-wind-forecast`).
4. Fill in the service configuration:
   - **Name:** `gridbricks-wind-backend`
   - **Region:** Frankfurt (EU) or Oregon (US)
   - **Branch:** `main`
   - **Root Directory:** *(leave blank)*
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
5. Under **Environment Variables**, add:
   - `PYTHONPATH` = `.`
   - `ENVIRONMENT` = `production`
6. Click **Deploy Web Service**.
7. Once deployed, copy your live backend URL (e.g., `https://gridbricks-wind-backend.onrender.com`).
8. Verify it by visiting `https://<YOUR-RENDER-APP>.onrender.com/api/health` — it will return `{"status":"healthy"}`.

---

### Part 3: Deploy Frontend to Vercel

1. Sign up or log into [Vercel.com](https://vercel.com).
2. Click **Add New...** > **Project** and import your GitHub repository.
3. In the project configure screen:
   - **Framework Preset:** `Vite`
   - **Root Directory:** Click `Edit` and select `frontend`
4. Expand **Environment Variables** and add:
   - `VITE_API_URL` = `https://<YOUR-RENDER-APP>.onrender.com` *(your live Render backend URL from Part 2)*
5. Click **Deploy**.
6. Once deployment finishes in ~30 seconds, Vercel will provide your live URL (e.g., `https://kjhwr-wind-forecast.vercel.app`).
7. Open the Vercel URL in your browser to verify that the charts, KPIs, and controls load live data from your Render backend.

---
