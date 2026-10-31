# Pocket Job Agent MVP

A minimal mobile-friendly PWA and FastAPI backend for job-profile matching and application tracking. This initial version deliberately uses manually entered job listings; it does not scrape portals or submit applications.

## Run locally (Windows)
1. Install Python 3.11+.
2. Open PowerShell in this folder.
3. Create a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

4. Open http://127.0.0.1:8000. Data is stored in `jobs.db`.

## iPhone access
To use it on an iPhone while your laptop is off, deploy the backend to an always-on cloud host and use HTTPS. Do not expose this starter publicly as-is: add authentication, rate limiting, secret management, and backups first. On iPhone Safari, open the deployed HTTPS URL → Share → Add to Home Screen.

## Current features
- Editable target roles, skills, locations, and salary preference.
- Simple explainable heuristic match score.
- Add job details and URL; reject duplicate URLs.
- Status tracking: Saved, Ready to apply, Applied, Interview, Rejected, Skipped.
- SQLite persistence and mobile-first layout.

## Lightweight changes
- No frontend framework, build tool, or cloud dependency: the interface is plain HTML/CSS/JavaScript.
- The server uses core Uvicorn only; install `uvicorn[standard]` only if you specifically need development auto-reload.
- Job scores are calculated when a job or profile changes, not whenever the jobs screen refreshes.
- The service worker caches only app-shell files and never caches API data, keeping storage small and job data current.

## Next steps
1. Add authentication and secure deployment.
2. Add job import via CSV / permitted feeds / official APIs.
3. Add daily scheduled discovery and notifications.
4. Add application preparation and portal-specific, permitted workflows with human review for uncertain questions.
