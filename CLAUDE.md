# Tryll Assistant Evaluation Dashboard

## Overview
FastAPI web dashboard for viewing and comparing RAG evaluation test reports for Tryll Assistant. Hosted on Render.

**Live URL:** https://testllmsite.onrender.com
**GitHub:** https://github.com/Skizziik/Testllmsite

## Project Structure
```
testllmsite/
├── app.py              # FastAPI backend
├── index.html          # Dashboard frontend (single page)
├── requirements.txt    # Python dependencies
├── render.yaml         # Render deployment config
└── reports_html/       # HTML evaluation reports (auto-pushed)
```

## Tech Stack
- **Backend:** FastAPI + Uvicorn
- **Frontend:** Vanilla HTML/CSS/JS (dark theme, Inter font)
- **Parsing:** BeautifulSoup4 for extracting report metadata
- **Hosting:** Render.com (free tier, 15-min sleep timeout)

## Key Features
- View all evaluation reports with filters (model, date, chunks, min score)
- Sort by date/score/questions (3 states: desc → asc → reset)
- Open reports in fullscreen modal
- Compare up to 5 reports side-by-side
- Auto-apply filters on change

## API Endpoints
- `GET /` - Serve dashboard
- `GET /api/reports` - List all reports with metadata
- `GET /api/report/{id}` - Get single report details
- `GET /api/compare?ids=id1,id2` - Compare multiple reports
- `GET /reports/{filename}` - Serve individual HTML report
- `GET /health` - Health check for Render

## Report Filename Format
```
evaluation_report_DD_MM_HH-MMAM/PM_Model_Name.html
```
Example: `evaluation_report_06_01_03-06AM_Llama_3.1_8B_Instruct_Q4_K_M.html`

## Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
# or
uvicorn app:app --reload --port 8000
```

## Deployment
Auto-deploys on push to master branch via Render.

Reports are auto-pushed from `run_evaluation_v3.py` after each test run.

## CSS Theme
- Background: `#000000` with blue radial gradient
- Font: Inter
- Accent: `#3B82F6` (blue)
- Cards: `rgba(255, 255, 255, 0.03)` backdrop
