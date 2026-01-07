# Tryll RAG Test Dashboard

## Overview
FastAPI web dashboard for RAG evaluation and testing for Tryll Assistant (Minecraft AI companion).

**Live URL:** https://testllmsite.onrender.com
**GitHub:** https://github.com/Skizziik/Testllmsite

---

## Project Structure
```
testllmsite/
├── app.py                    # FastAPI backend - all API endpoints
├── index.html                # Dashboard - LLM evaluation reports with filters
├── coverage.html             # Coverage Map - knowledge base test coverage
├── rag-tests.html            # RAG Tests - RAG-only accuracy tests
├── rag-dynamic.html          # Dynamic Parameter Tests - k x threshold heatmap
├── requirements.txt          # Python dependencies (fastapi, uvicorn, beautifulsoup4)
├── render.yaml               # Render.com deployment config
├── CLAUDE.md                 # This documentation
│
├── reports_html/             # LLM evaluation HTML reports (auto-pushed)
├── rag_results/              # RAG-only test results (JSON)
├── rag_results_dinamic/      # Dynamic parameter test sessions
│   └── {timestamp}/
│       ├── summary.json      # Accuracy matrix for heatmap (small, loads fast)
│       ├── metadata.json     # Questions, config info
│       └── runs/             # Individual run files (lazy loading)
│           ├── k1_t0.1.json
│           ├── k1_t0.2.json
│           └── ...
└── coverage_data/            # Coverage test data
    ├── coverage_results.json
    └── chunks_index.json
```

---

## Pages & Navigation

All pages share unified navigation bar with 4 buttons:
```html
<div class="nav-buttons">
    <a href="/" class="nav-btn">Dashboard</a>
    <a href="/coverage" class="nav-btn">Coverage Map</a>
    <a href="/rag-tests" class="nav-btn">RAG Tests</a>
    <a href="/rag-dynamic" class="nav-btn">Dynamic Parameter Tests</a>
</div>
```
Current page has `class="nav-btn active"`.

### 1. Dashboard (`/`, `index.html`)
- LLM evaluation reports with filters (model, date, chunks, score)
- Sort by date/score/questions
- Open reports in fullscreen modal
- Compare up to 5 reports side-by-side

### 2. Coverage Map (`/coverage`, `coverage.html`)
- Minecraft knowledge base test coverage visualization
- Category/article breakdown
- Chunk-level status (tested/untested/found/missed)

### 3. RAG Tests (`/rag-tests`, `rag-tests.html`)
- RAG-only accuracy tests (no LLM, just retrieval)
- Shows which chunks were found/missed
- Click test to see individual results with chunk highlighting

### 4. Dynamic Parameter Tests (`/rag-dynamic`, `rag-dynamic.html`)
- Tests RAG with varying parameters: k (1-5) x threshold (0.1-1.0)
- 50 test combinations per session
- Heatmap visualization with color coding
- Line chart showing accuracy vs threshold for each k
- Click cell to see detailed results (lazy loaded)

---

## API Endpoints

### Dashboard
- `GET /` - Serve dashboard page
- `GET /api/reports` - List all LLM reports with metadata
- `GET /api/report/{id}` - Get single report details
- `GET /api/compare?ids=id1,id2` - Compare multiple reports
- `GET /reports/{filename}` - Serve individual HTML report

### Coverage
- `GET /coverage` - Serve coverage page
- `GET /api/coverage` - Get coverage results
- `GET /api/coverage/stats` - Coverage statistics summary
- `GET /api/coverage/chunks` - Chunks index
- `GET /api/coverage/tree` - Tree structure for visualization
- `GET /api/coverage/chunk/{chunk_id}` - Single chunk details

### RAG Tests
- `GET /rag-tests` - Serve RAG tests page
- `GET /api/rag-tests` - List all RAG test results
- `GET /api/rag-tests/{test_id}` - Get specific test details
- `GET /api/server-config` - Current TryllServer config

### Dynamic Parameter Tests
- `GET /rag-dynamic` - Serve dynamic tests page
- `GET /api/rag-dynamic-sessions` - List all test sessions
- `GET /api/rag-dynamic-session/{timestamp}` - Get session summary + accuracy matrix
- `GET /api/rag-dynamic-run/{timestamp}/{k}/{threshold}` - Get specific run (lazy loading)

### Health
- `GET /health` (GET + HEAD) - Health check for Render/UptimeRobot

---

## CSS Design System

### Colors
```css
/* Background */
background: #000000;
background-image: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.15), transparent);

/* Primary accent (blue) */
#3B82F6

/* Success (green) */
#10B981

/* Warning (orange) */
#F59E0B

/* Error (red) */
#EF4444

/* Text */
color: rgba(255, 255, 255, 0.9);      /* Primary */
color: rgba(255, 255, 255, 0.65);     /* Secondary */
color: rgba(255, 255, 255, 0.45);     /* Muted */

/* Borders */
border: 1px solid rgba(255, 255, 255, 0.08);
```

### Typography
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
```
Load via Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
```

### Common Components

#### Cards/Sections
```css
.section {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(10px);
    border-radius: 12px;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 30px;
}
```

#### Buttons
```css
.nav-btn {
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #3B82F6;
    padding: 10px 24px;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 500;
    transition: all 0.2s ease;
}

.nav-btn:hover {
    background: #3B82F6;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.nav-btn.active {
    background: #3B82F6;
    color: #ffffff;
}
```

#### Accuracy Badges
```css
.accuracy-high { color: #10B981; }    /* >= 80% */
.accuracy-medium { color: #F59E0B; }  /* >= 50% */
.accuracy-low { color: #EF4444; }     /* < 50% */
```

#### Heatmap Colors
```css
/* >= 85% */ background: #10B981;
/* >= 70% */ background: #84CC16;
/* >= 50% */ background: #F59E0B;
/* < 50%  */ background: #EF4444;
```

#### Modal
```css
.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal {
    background: #000000;
    background-image: radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.1), transparent);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    max-width: 800px;
    max-height: 80vh;
}
```

#### Loading Spinner
```css
.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(59, 130, 246, 0.2);
    border-top-color: #3B82F6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

#### Highlight Matched Chunk (green)
```css
.chunk-match, code.found {
    background: rgba(16, 185, 129, 0.3);
    color: #10B981;
    font-weight: 600;
}
```

---

## Data Formats

### RAG Test Result (rag_results/*.json)
```json
{
  "timestamp": "2026_01_07-18_58",
  "total_tests": 50,
  "correct": 42,
  "accuracy": 84.0,
  "rag_chunks_number": 3,
  "mistral_model": "mistral-large-latest",
  "server_config": { ... },
  "results": [
    {
      "chunk_id": "leather_tunic",
      "question": "What is the chance for a zombie to drop...",
      "returned_chunks": ["leather_tunic", "leather_pants", "leggings"],
      "found": true
    }
  ]
}
```

### Dynamic Test Session Summary (rag_results_dinamic/{ts}/summary.json)
```json
{
  "test_type": "RAG-dynamic",
  "timestamp": "2026_01_07-20_40_20",
  "questions_count": 100,
  "total_runs": 50,
  "accuracy_matrix": {
    "1": { "0.1": 75.0, "0.2": 75.0, ... },
    "2": { "0.1": 88.0, ... },
    ...
  }
}
```

### Individual Run (rag_results_dinamic/{ts}/runs/k3_t0.2.json)
```json
{
  "rag_chunks_number": 3,
  "rag_score_threshold": 0.2,
  "total_tests": 100,
  "correct": 92,
  "accuracy": 92.0,
  "results": [ ... ]
}
```

---

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
# or
uvicorn app:app --reload --port 8000

# Access at http://localhost:8000
```

## Deployment

Auto-deploys on push to master via Render.com.

```bash
# Push changes
git add -A && git commit -m "message" && git push
```

Render will auto-rebuild and deploy (takes ~2-3 minutes).

---

## Related Test Scripts (in autotest/)

- `run_evaluation_v3.py` - Full LLM evaluation (generates reports_html/)
- `rag_tester/rag_tester.py` - RAG-only tests (generates rag_results/)
- `rag_tester/rag_tester_dynamic.py` - Dynamic parameter tests (generates rag_results_dinamic/)
- `coverage/coverage_test.py` - Coverage tests (generates coverage_data/)

All scripts auto-push results to GitHub after completion.
