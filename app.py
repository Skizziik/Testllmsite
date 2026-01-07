"""
Tryll RAG Test Dashboard - FastAPI Backend
Serves HTML reports and provides API for comparison
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import re
import json
from bs4 import BeautifulSoup
from typing import Optional
import os

app = FastAPI(title="Tryll RAG Test Dashboard")

# Get the directory where this script is located
BASE_DIR = Path(__file__).parent
REPORTS_DIR = BASE_DIR / "reports_html"

# Ensure reports directory exists
REPORTS_DIR.mkdir(exist_ok=True)


def parse_html_report(filepath: Path) -> dict:
    """Parse an HTML report file and extract metadata."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        soup = BeautifulSoup(content, 'html.parser')

        # Extract data from filename
        filename = filepath.name
        # Format: evaluation_report_DD_MM_HH-MMAM/PM_Model_Name.html
        # Example: evaluation_report_06_01_03-06AM_Llama_3.1_8B_Instruct_Q4_K_M.html

        report_data = {
            'id': filepath.stem,
            'filename': filename,
            'model': 'Unknown',
            'date': '',
            'time': '',
            'score_percent': 0,
            'questions_count': 0,
            'server_config': {},
            'test_config': {},
            'questions': []
        }

        # Try to extract from subtitle
        subtitle = soup.select_one('.header .subtitle')
        if subtitle:
            text = subtitle.get_text()
            # Generated: 2026-01-06 03:06 | Questions: 15 | Model: Llama 3.1 8B Instruct (Q4_K_M)
            match = re.search(r'Generated:\s*(\d{4}-\d{2}-\d{2})\s*(\d{2}:\d{2})', text)
            if match:
                report_data['date'] = match.group(1)
                report_data['time'] = match.group(2)

            match = re.search(r'Questions:\s*(\d+)', text)
            if match:
                report_data['questions_count'] = int(match.group(1))

            match = re.search(r'Model:\s*(.+?)(?:\||$)', text)
            if match:
                report_data['model'] = match.group(1).strip()

        # Try to get model from filename if not found in subtitle
        if report_data['model'] == 'Unknown':
            # Try to extract model name from filename
            parts = filename.replace('.html', '').split('_')
            if len(parts) > 4:
                # Skip date/time parts and join the rest
                model_parts = parts[5:] if len(parts) > 5 else parts[4:]
                report_data['model'] = ' '.join(model_parts).replace('_', ' ')

        # Extract score from metrics
        score_card = soup.select_one('.metric-card.highlight .value')
        if score_card:
            text = score_card.get_text()
            # Format: "548/750" or just percentage
            match = re.search(r'(\d+(?:\.\d+)?)', text)
            if match:
                # Try to find the percentage in subtext
                subtext = soup.select_one('.metric-card.highlight .subtext')
                if subtext:
                    pct_match = re.search(r'(\d+(?:\.\d+)?)%', subtext.get_text())
                    if pct_match:
                        report_data['score_percent'] = float(pct_match.group(1))

        # If score not found in highlight card, try to find it elsewhere
        if report_data['score_percent'] == 0:
            for card in soup.select('.metric-card'):
                label = card.select_one('.label')
                if label and 'score' in label.get_text().lower():
                    value = card.select_one('.value')
                    if value:
                        match = re.search(r'(\d+(?:\.\d+)?)', value.get_text())
                        if match:
                            report_data['score_percent'] = float(match.group(1))
                            break

        # Extract server config from modal
        server_config_modal = soup.select_one('#serverConfigModal .prompt-text')
        if server_config_modal:
            config_text = server_config_modal.get_text()
            # Clean up HTML entities and parse JSON
            config_text = config_text.replace('\n', '').replace('<br>', '')
            try:
                # Try to extract JSON-like structure
                config_text = re.sub(r'<[^>]+>', '', str(server_config_modal))
                config_text = config_text.replace('&quot;', '"').replace('&amp;', '&')
                config_text = config_text.replace('\n', '').strip()
                # Find JSON object
                json_match = re.search(r'\{[^{}]*\}', config_text, re.DOTALL)
                if json_match:
                    report_data['server_config'] = json.loads(json_match.group())
            except (json.JSONDecodeError, AttributeError):
                pass

        # Extract test config (temperature, etc.)
        test_config_modal = soup.select_one('#promptModal .model-info')
        if test_config_modal:
            model_text = test_config_modal.get_text()
            report_data['test_config']['model'] = model_text.replace('Model:', '').strip()

        # Extract questions and answers from table
        table_rows = soup.select('.results-table tbody tr:not(.details-row)')
        for row in table_rows:
            cells = row.select('td')
            if len(cells) >= 4:
                question_cell = cells[1]
                answer_cell = cells[2]
                score_cell = cells[3]

                question_text = question_cell.select_one('.question-text')
                if question_text:
                    q_data = {
                        'question': question_text.get_text().strip(),
                        'answer': answer_cell.get_text().strip(),
                        'score': 0
                    }

                    # Extract score
                    score_badge = score_cell.select_one('.score-badge')
                    if score_badge:
                        match = re.search(r'(\d+)', score_badge.get_text())
                        if match:
                            q_data['score'] = int(match.group(1))

                    report_data['questions'].append(q_data)

        return report_data

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return {
            'id': filepath.stem,
            'filename': filepath.name,
            'model': 'Parse Error',
            'date': '',
            'time': '',
            'score_percent': 0,
            'questions_count': 0,
            'server_config': {},
            'test_config': {},
            'questions': [],
            'error': str(e)
        }


@app.get("/")
async def root():
    """Serve the main dashboard page."""
    index_path = BASE_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/api/reports")
async def get_reports():
    """Get list of all reports with metadata."""
    reports = []

    if not REPORTS_DIR.exists():
        return reports

    for filepath in sorted(REPORTS_DIR.glob("*.html"), key=lambda x: x.stat().st_mtime, reverse=True):
        report_data = parse_html_report(filepath)
        # Don't include full questions in list view
        report_data.pop('questions', None)
        reports.append(report_data)

    return reports


@app.get("/api/compare")
async def compare_reports(ids: str):
    """Get detailed data for comparing multiple reports by question index."""
    report_ids = ids.split(',')

    reports = []
    reports_with_questions = []

    for report_id in report_ids:
        filepath = REPORTS_DIR / f"{report_id}.html"
        if not filepath.exists():
            # Try with common extensions
            for ext in ['', '.html']:
                test_path = REPORTS_DIR / f"{report_id}{ext}"
                if test_path.exists():
                    filepath = test_path
                    break

        if filepath.exists():
            report_data = parse_html_report(filepath)
            reports_with_questions.append(report_data)
            # Keep a copy without questions for response
            report_copy = {k: v for k, v in report_data.items() if k != 'questions'}
            reports.append(report_copy)

    # Find max number of questions across all reports
    max_questions = max((len(r.get('questions', [])) for r in reports_with_questions), default=0)

    # Build questions by index (Q1 vs Q1, Q2 vs Q2, etc.)
    questions_by_index = []
    for i in range(max_questions):
        question_data = {
            'index': i + 1,
            'answers': []
        }

        for report in reports_with_questions:
            report_questions = report.get('questions', [])
            if i < len(report_questions):
                q = report_questions[i]
                question_data['answers'].append({
                    'report_id': report['id'],
                    'model': report.get('model', 'Unknown'),
                    'date': report.get('date', ''),
                    'question': q['question'],
                    'answer': q['answer'],
                    'score': q['score'],
                    'score_percent': (q['score'] / 50) * 100 if q['score'] else 0
                })
            else:
                # No question at this index - add empty placeholder
                question_data['answers'].append({
                    'report_id': report['id'],
                    'model': report.get('model', 'Unknown'),
                    'date': report.get('date', ''),
                    'question': None,
                    'answer': None,
                    'score': None,
                    'score_percent': None
                })

        questions_by_index.append(question_data)

    return {
        'reports': reports,
        'questions': questions_by_index
    }


@app.get("/api/report/{report_id}")
async def get_report(report_id: str):
    """Get full details of a single report."""
    filepath = REPORTS_DIR / f"{report_id}.html"
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    return parse_html_report(filepath)


# Serve static HTML reports
@app.get("/reports/{filename:path}")
async def serve_report(filename: str):
    """Serve individual HTML report files."""
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(filepath, media_type="text/html")


# Health check for Render (supports both GET and HEAD for UptimeRobot)
@app.head("/health")
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# ============================================================
# COVERAGE MAP API
# ============================================================

COVERAGE_DATA_DIR = BASE_DIR / "coverage_data"


def load_coverage_data(filename: str) -> dict:
    """Load a coverage data file."""
    filepath = COVERAGE_DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


@app.get("/coverage")
async def coverage_page():
    """Serve the coverage map page."""
    coverage_path = BASE_DIR / "coverage.html"
    if coverage_path.exists():
        return FileResponse(coverage_path)
    # Fallback to inline HTML if file doesn't exist
    return HTMLResponse(content="""
    <html>
    <head><title>Coverage Map - Coming Soon</title></head>
    <body style="background:#1a1a2e;color:white;font-family:sans-serif;text-align:center;padding:50px;">
        <h1>Coverage Map</h1>
        <p>Coverage visualization coming soon...</p>
        <p><a href="/" style="color:#00ff00;">Back to Dashboard</a></p>
    </body>
    </html>
    """)


@app.get("/api/coverage")
async def get_coverage():
    """Get coverage results."""
    return load_coverage_data("coverage_results.json")


@app.get("/api/coverage/stats")
async def get_coverage_stats():
    """Get coverage statistics summary."""
    coverage = load_coverage_data("coverage_results.json")
    index = load_coverage_data("chunks_index.json")

    if not coverage and not index:
        return {
            "overall": {
                "total_chunks": 0,
                "tested_chunks": 0,
                "coverage_percent": 0,
                "rag_accuracy": 0,
                "llm_avg_score": 0
            },
            "by_category": {},
            "last_updated": None
        }

    # Build category stats
    category_stats = {}
    results = coverage.get("results", {})
    chunks = index.get("chunks", {})

    for chunk_id, chunk_info in chunks.items():
        category = chunk_info.get("category", "Other")
        if category not in category_stats:
            category_stats[category] = {
                "total": 0,
                "tested": 0,
                "rag_found": 0
            }

        category_stats[category]["total"] += 1

        if chunk_id in results:
            result = results[chunk_id]
            category_stats[category]["tested"] += 1
            if result.get("rag_found_chunk", False):
                category_stats[category]["rag_found"] += 1

    # Calculate percentages
    for cat, stats in category_stats.items():
        stats["coverage_percent"] = round(
            (stats["tested"] / stats["total"]) * 100, 2
        ) if stats["total"] > 0 else 0
        stats["rag_accuracy"] = round(
            (stats["rag_found"] / stats["tested"]) * 100, 2
        ) if stats["tested"] > 0 else 0

    return {
        "overall": {
            "total_chunks": coverage.get("total_chunks", index.get("total_chunks", 0)),
            "tested_chunks": coverage.get("tested_chunks", 0),
            "coverage_percent": coverage.get("coverage_percent", 0),
            "rag_accuracy": coverage.get("rag_accuracy", 0),
            "llm_avg_score": coverage.get("llm_avg_score", 0)
        },
        "by_category": category_stats,
        "last_updated": coverage.get("last_updated")
    }


@app.get("/api/coverage/chunks")
async def get_chunks_index():
    """Get chunks index."""
    return load_coverage_data("chunks_index.json")


@app.get("/api/coverage/tree")
async def get_coverage_tree():
    """Get coverage data as a tree structure for visualization."""
    coverage = load_coverage_data("coverage_results.json")
    index = load_coverage_data("chunks_index.json")

    results = coverage.get("results", {})
    chunks = index.get("chunks", {})

    # Build tree: Category -> Article -> Chunks
    tree = {}

    for chunk_id, chunk_info in chunks.items():
        category = chunk_info.get("category", "Other")
        article = chunk_info.get("article", "Unknown")

        if category not in tree:
            tree[category] = {
                "name": category,
                "articles": {},
                "stats": {"total": 0, "tested": 0, "rag_found": 0}
            }

        if article not in tree[category]["articles"]:
            tree[category]["articles"][article] = {
                "name": article,
                "chunks": [],
                "stats": {"total": 0, "tested": 0, "rag_found": 0}
            }

        # Determine chunk status
        result = results.get(chunk_id)
        if result:
            if result.get("rag_found_chunk"):
                status = "rag_found"
                tree[category]["stats"]["rag_found"] += 1
                tree[category]["articles"][article]["stats"]["rag_found"] += 1
            else:
                status = "rag_missed"
            tree[category]["stats"]["tested"] += 1
            tree[category]["articles"][article]["stats"]["tested"] += 1
        else:
            status = "untested"

        tree[category]["stats"]["total"] += 1
        tree[category]["articles"][article]["stats"]["total"] += 1

        tree[category]["articles"][article]["chunks"].append({
            "id": chunk_id,
            "status": status,
            "preview": chunk_info.get("text_preview", "")[:100] if chunk_info.get("text_preview") else ""
        })

    # Convert articles dict to list
    for category in tree.values():
        category["articles"] = list(category["articles"].values())

    return {
        "categories": list(tree.values()),
        "stats": {
            "total": index.get("total_chunks", 0),
            "tested": coverage.get("tested_chunks", 0),
            "coverage_percent": coverage.get("coverage_percent", 0),
            "rag_accuracy": coverage.get("rag_accuracy", 0)
        }
    }


@app.get("/api/coverage/chunk/{chunk_id}")
async def get_chunk_details(chunk_id: str):
    """Get details for a specific chunk."""
    coverage = load_coverage_data("coverage_results.json")
    index = load_coverage_data("chunks_index.json")

    chunk_info = index.get("chunks", {}).get(chunk_id)
    if not chunk_info:
        raise HTTPException(status_code=404, detail="Chunk not found")

    result = coverage.get("results", {}).get(chunk_id)

    return {
        "chunk": chunk_info,
        "test_result": result
    }


# ============================================================
# RAG-ONLY TESTS API
# ============================================================

RAG_TESTS_DIR = BASE_DIR / "rag_results"


@app.get("/rag-tests")
async def rag_tests_page():
    """Serve the RAG tests page."""
    rag_tests_path = BASE_DIR / "rag-tests.html"
    if rag_tests_path.exists():
        return FileResponse(rag_tests_path)
    raise HTTPException(status_code=404, detail="RAG tests page not found")


@app.get("/api/rag-tests")
async def get_rag_tests():
    """Get list of all RAG-only test results."""
    results = []

    if not RAG_TESTS_DIR.exists():
        return results

    for filepath in sorted(RAG_TESTS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append(data)
        except (json.JSONDecodeError, Exception) as e:
            print(f"Error loading {filepath}: {e}")

    return results


@app.get("/api/rag-tests/{test_id}")
async def get_rag_test_detail(test_id: str):
    """Get details of a specific RAG test."""
    filepath = RAG_TESTS_DIR / f"{test_id}.json"
    if not filepath.exists():
        # Try to find by timestamp
        for f in RAG_TESTS_DIR.glob("*.json"):
            if test_id in f.stem:
                filepath = f
                break

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="RAG test not found")

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get("/api/server-config")
async def get_server_config():
    """Get TryllServer configuration."""
    config_path = Path("C:/Users/utente/AppData/Local/Tryll/server/config.json")
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Server config not found")

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# RAG DYNAMIC TESTS API
# ============================================================

RAG_DYNAMIC_DIR = BASE_DIR / "rag_results_dinamic"


@app.get("/rag-dynamic")
async def rag_dynamic_page():
    """Serve the RAG dynamic tests page."""
    rag_dynamic_path = BASE_DIR / "rag-dynamic.html"
    if rag_dynamic_path.exists():
        return FileResponse(rag_dynamic_path)
    raise HTTPException(status_code=404, detail="RAG dynamic tests page not found")


@app.get("/api/rag-dynamic-sessions")
async def get_rag_dynamic_sessions():
    """Get list of all dynamic RAG test sessions."""
    sessions = []

    if not RAG_DYNAMIC_DIR.exists():
        return sessions

    for session_dir in sorted(RAG_DYNAMIC_DIR.iterdir(), key=lambda x: x.name, reverse=True):
        if session_dir.is_dir():
            summary_file = session_dir / "summary.json"
            if summary_file.exists():
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                        sessions.append({
                            "timestamp": session_dir.name,
                            "questions_count": summary.get("questions_count", 0),
                            "total_runs": summary.get("total_runs", 0)
                        })
                except (json.JSONDecodeError, Exception) as e:
                    print(f"Error loading {summary_file}: {e}")

    return sessions


@app.get("/api/rag-dynamic-session/{timestamp}")
async def get_rag_dynamic_session(timestamp: str):
    """Get details of a specific dynamic RAG test session."""
    session_dir = RAG_DYNAMIC_DIR / timestamp

    if not session_dir.exists() or not session_dir.is_dir():
        raise HTTPException(status_code=404, detail="Session not found")

    summary_file = session_dir / "summary.json"
    if not summary_file.exists():
        raise HTTPException(status_code=404, detail="Session summary not found")

    with open(summary_file, 'r', encoding='utf-8') as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
