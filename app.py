from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent
DB = ROOT / "jobs.db"


def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    # Better responsiveness if the app is opened in more than one browser tab.
    c.execute('PRAGMA journal_mode=WAL')
    return c

@asynccontextmanager
async def lifespan(app: FastAPI):
    with conn() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, company TEXT DEFAULT '',
          location TEXT DEFAULT '', url TEXT NOT NULL UNIQUE, description TEXT DEFAULT '',
          source TEXT DEFAULT 'Manual', score INTEGER DEFAULT 0, status TEXT DEFAULT 'Saved',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('CREATE INDEX IF NOT EXISTS jobs_score_created_idx ON jobs(score DESC, created_at DESC)')
        c.execute('''CREATE TABLE IF NOT EXISTS profile (
          id INTEGER PRIMARY KEY CHECK(id=1), roles TEXT, skills TEXT, locations TEXT,
          min_salary REAL DEFAULT 0)''')
        c.execute("INSERT OR IGNORE INTO profile(id,roles,skills,locations,min_salary) VALUES(1,?,?,?,?)",
                  ('Data Engineer, Azure Data Engineer, Big Data Engineer, MLOps Engineer',
                   'Python, SQL, PySpark, Spark, ETL, Azure, AWS, GCP, Airflow, Databricks, Redshift, Glue, Machine Learning, MLOps',
                   'India, Remote, Mumbai, Pune', 11))
    yield

app = FastAPI(title="Pocket Job Agent", lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

class JobIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    company: str = ''
    location: str = ''
    url: str = Field(min_length=5, max_length=2000)
    description: str = ''
    source: str = 'Manual'

class ProfileIn(BaseModel):
    roles: str
    skills: str
    locations: str
    min_salary: float = 0

class StatusIn(BaseModel):
    status: str

@app.get('/')
def home():
    return FileResponse(ROOT / 'static' / 'index.html')

@app.get('/api/profile')
def get_profile():
    with conn() as c:
        r = c.execute('SELECT roles,skills,locations,min_salary FROM profile WHERE id=1').fetchone()
        return dict(r)

@app.put('/api/profile')
def update_profile(p: ProfileIn):
    with conn() as c:
        c.execute('UPDATE profile SET roles=?,skills=?,locations=?,min_salary=? WHERE id=1',
                  (p.roles,p.skills,p.locations,p.min_salary))
    recalculate_scores()
    return {'ok': True}

def score_job(job, profile):
    title = job['title'].lower()
    desc = (job['description'] or '').lower()
    loc = (job['location'] or '').lower()
    roles = [x.strip().lower() for x in profile['roles'].split(',') if x.strip()]
    skills = [x.strip().lower() for x in profile['skills'].split(',') if x.strip()]
    locations = [x.strip().lower() for x in profile['locations'].split(',') if x.strip()]
    score = 0
    if any(r in title for r in roles): score += 40
    elif any(any(word in title for word in r.split()) for r in roles): score += 20
    if skills:
        score += min(40, round(40 * sum(1 for s in skills if s in desc or s in title) / len(skills)))
    if any(l in loc for l in locations): score += 15
    if job['url'].startswith('https://'): score += 5
    return min(100, score)

def recalculate_scores():
    with conn() as c:
        p = dict(c.execute('SELECT roles,skills,locations,min_salary FROM profile WHERE id=1').fetchone())
        rows = c.execute('SELECT * FROM jobs').fetchall()
        for row in rows:
            c.execute('UPDATE jobs SET score=? WHERE id=?', (score_job(dict(row),p),row['id']))

@app.get('/api/jobs')
def list_jobs():
    with conn() as c:
        rows = c.execute('SELECT * FROM jobs ORDER BY score DESC, created_at DESC').fetchall()
        return [dict(r) for r in rows]

@app.post('/api/jobs')
def add_job(j: JobIn):
    with conn() as c:
        p = dict(c.execute('SELECT roles,skills,locations,min_salary FROM profile WHERE id=1').fetchone())
        try:
            cur = c.execute('INSERT INTO jobs(title,company,location,url,description,source,score) VALUES(?,?,?,?,?,?,?)',
                (j.title,j.company,j.location,j.url,j.description,j.source,score_job(j.model_dump(),p)))
        except sqlite3.IntegrityError:
            raise HTTPException(409, 'This job URL is already saved.')
        return {'id': cur.lastrowid, 'score': score_job(j.model_dump(),p)}

@app.patch('/api/jobs/{job_id}')
def update_status(job_id: int, data: StatusIn):
    allowed = {'Saved','Ready to apply','Applied','Rejected','Interview','Skipped'}
    if data.status not in allowed: raise HTTPException(400, 'Invalid status')
    with conn() as c:
        cur = c.execute('UPDATE jobs SET status=? WHERE id=?',(data.status,job_id))
        if not cur.rowcount: raise HTTPException(404,'Job not found')
    return {'ok':True}

@app.delete('/api/jobs/{job_id}')
def delete_job(job_id: int):
    with conn() as c:
        c.execute('DELETE FROM jobs WHERE id=?',(job_id,))
    return {'ok':True}
