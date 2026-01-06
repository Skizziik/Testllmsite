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
                        'answer': answer_cell.get_text().strip()[:1000],  # Limit answer length
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
    """Get detailed data for comparing multiple reports."""
    report_ids = ids.split(',')

    reports = []
    all_questions = {}

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
            reports.append(report_data)

            # Collect questions
            for i, q in enumerate(report_data.get('questions', [])):
                q_key = q['question'][:100]  # Use first 100 chars as key
                if q_key not in all_questions:
                    all_questions[q_key] = {
                        'question': q['question'],
                        'answers': []
                    }
                all_questions[q_key]['answers'].append({
                    'report_id': report_data['id'],
                    'model': report_data.get('model', 'Unknown'),
                    'date': report_data.get('date', ''),
                    'answer': q['answer'],
                    'score': q['score'],
                    'score_percent': (q['score'] / 50) * 100 if q['score'] else 0
                })

    # Clean up report data for response
    for report in reports:
        report.pop('questions', None)

    return {
        'reports': reports,
        'questions': list(all_questions.values())
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


# Health check for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
