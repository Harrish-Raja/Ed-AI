import sqlite3
import json
import os
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "edai.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        level TEXT DEFAULT 'Beginner',
        daily_hours REAL DEFAULT 2.0,
        target_goal TEXT DEFAULT 'Skill Mastery',
        preferred_language TEXT DEFAULT 'Python',
        avatar_color TEXT DEFAULT '#6C63FF',
        created_at TEXT DEFAULT (datetime('now')),
        last_active TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS roadmaps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        goal TEXT,
        level TEXT,
        duration_weeks INTEGER DEFAULT 8,
        roadmap_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roadmap_id INTEGER,
        user_id INTEGER,
        topic_name TEXT,
        parent_topic TEXT,
        week_number INTEGER DEFAULT 1,
        day_number INTEGER DEFAULT 1,
        order_idx INTEGER DEFAULT 0,
        status TEXT DEFAULT 'locked',
        mastery_pct REAL DEFAULT 0.0,
        estimated_hours REAL DEFAULT 1.0,
        FOREIGN KEY(roadmap_id) REFERENCES roadmaps(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS study_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_id INTEGER,
        topic_name TEXT,
        duration_mins REAL DEFAULT 0,
        xp_earned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS quiz_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_id INTEGER,
        topic_name TEXT,
        score INTEGER DEFAULT 0,
        total INTEGER DEFAULT 5,
        percentage REAL DEFAULT 0.0,
        answers_json TEXT,
        time_taken_secs INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS code_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_id INTEGER,
        topic_name TEXT,
        problem_title TEXT,
        code TEXT,
        output TEXT,
        feedback_json TEXT,
        status TEXT DEFAULT 'submitted',
        xp_earned INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS performance_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        xp_earned INTEGER DEFAULT 0,
        study_mins REAL DEFAULT 0,
        quiz_accuracy REAL DEFAULT 0,
        topics_completed INTEGER DEFAULT 0,
        streak_day INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS interview_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        job_role TEXT,
        questions_json TEXT,
        responses_json TEXT,
        score REAL DEFAULT 0.0,
        feedback TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS study_content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic_id INTEGER,
        topic_name TEXT,
        language TEXT,
        level TEXT,
        content_json TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    conn.commit()

    # ── Safe schema migrations (run on every startup, silently skip if already done) ──
    # These handle old DBs created before column renames or additions.
    _migrations = [
        # study_sessions: some old versions used 'study_mins' instead of 'duration_mins'
        "ALTER TABLE study_sessions ADD COLUMN duration_mins REAL DEFAULT 0",
        # study_sessions: ensure xp_earned exists
        "ALTER TABLE study_sessions ADD COLUMN xp_earned INTEGER DEFAULT 0",
        # code_submissions: ensure all columns exist
        "ALTER TABLE code_submissions ADD COLUMN problem_title TEXT",
        "ALTER TABLE code_submissions ADD COLUMN feedback_json TEXT",
        "ALTER TABLE code_submissions ADD COLUMN xp_earned INTEGER DEFAULT 0",
        # topics: ensure mastery_pct exists
        "ALTER TABLE topics ADD COLUMN mastery_pct REAL DEFAULT 0.0",
        # users: ensure preferred_language exists (old DBs might not have it)
        "ALTER TABLE users ADD COLUMN preferred_language TEXT DEFAULT 'Python'",
        "ALTER TABLE users ADD COLUMN daily_hours REAL DEFAULT 2.0",
    ]
    for migration in _migrations:
        try:
            c.execute(migration)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists — silently skip

    # If old DB has 'study_mins' column in study_sessions but not 'duration_mins':
    # copy data across so nothing is lost
    try:
        cols = [row[1] for row in c.execute("PRAGMA table_info(study_sessions)").fetchall()]
        if "study_mins" in cols and "duration_mins" in cols:
            c.execute("""
                UPDATE study_sessions
                SET duration_mins = study_mins
                WHERE duration_mins = 0 AND study_mins > 0
            """)
            conn.commit()
    except Exception:
        pass

    conn.close()



# ─── USER ────────────────────────────────────────────────
def create_user(name, email, level, daily_hours, target_goal, preferred_language):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""INSERT INTO users (name, email, level, daily_hours, target_goal, preferred_language)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (name, email, level, daily_hours, target_goal, preferred_language))
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        row = c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def get_user(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user(user_id, **kwargs):
    conn = get_connection()
    for key, val in kwargs.items():
        conn.execute(f"UPDATE users SET {key}=? WHERE id=?", (val, user_id))
    conn.execute("UPDATE users SET last_active=? WHERE id=?", (datetime.now().isoformat(), user_id))
    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM users ORDER BY last_active DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── ROADMAP ─────────────────────────────────────────────
def save_roadmap(user_id, topic, goal, level, duration_weeks, roadmap_json):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""INSERT INTO roadmaps (user_id, topic, goal, level, duration_weeks, roadmap_json)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, topic, goal, level, duration_weeks, json.dumps(roadmap_json)))
    rid = c.lastrowid
    conn.commit()
    conn.close()
    return rid


def get_latest_roadmap(user_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM roadmaps WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
                       (user_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["roadmap_json"] = json.loads(d["roadmap_json"]) if d["roadmap_json"] else {}
        return d
    return None


def get_all_roadmaps(user_id):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM roadmaps WHERE user_id=? ORDER BY created_at DESC",
                        (user_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["roadmap_json"] = json.loads(d["roadmap_json"]) if d["roadmap_json"] else {}
        result.append(d)
    return result


def get_roadmap_by_id(roadmap_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM roadmaps WHERE id=?", (roadmap_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["roadmap_json"] = json.loads(d["roadmap_json"]) if d["roadmap_json"] else {}
        return d
    return None


# ─── STUDY CONTENT ─────────────────────────────────────
def save_study_content(user_id, topic_id, topic_name, language, level, content_dict):
    """Persist AI-generated lesson content so it doesn’t need to be regenerated."""
    conn = get_connection()
    c = conn.cursor()
    # Upsert: update if exists, insert otherwise
    existing = c.execute(
        "SELECT id FROM study_content WHERE user_id=? AND topic_id=?",
        (user_id, topic_id)
    ).fetchone()
    if existing:
        c.execute(
            """UPDATE study_content
               SET content_json=?, language=?, level=?, updated_at=datetime('now')
               WHERE user_id=? AND topic_id=?""",
            (json.dumps(content_dict), language, level, user_id, topic_id)
        )
    else:
        c.execute(
            """INSERT INTO study_content
               (user_id, topic_id, topic_name, language, level, content_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, topic_id, topic_name, language, level, json.dumps(content_dict))
        )
    conn.commit()
    conn.close()


def get_study_content(user_id, topic_id):
    """Retrieve saved lesson content for a topic. Returns None if not cached."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM study_content WHERE user_id=? AND topic_id=? ORDER BY updated_at DESC LIMIT 1",
        (user_id, topic_id)
    ).fetchone()
    conn.close()
    if row:
        d = dict(row)
        try:
            d["content_dict"] = json.loads(d["content_json"])
        except Exception:
            d["content_dict"] = {}
        return d
    return None


# ─── TOPICS ──────────────────────────────────────────────
def save_topics(roadmap_id, user_id, topics_list):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM topics WHERE roadmap_id=?", (roadmap_id,))
    for i, t in enumerate(topics_list):
        c.execute("""INSERT INTO topics (roadmap_id, user_id, topic_name, parent_topic,
                     week_number, day_number, order_idx, status, estimated_hours)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (roadmap_id, user_id, t.get("name"), t.get("parent"),
                   t.get("week", 1), t.get("day", 1), i,
                   "available" if i == 0 else "locked",
                   t.get("hours", 1.0)))
    conn.commit()
    conn.close()


def get_topics(user_id, roadmap_id=None):
    conn = get_connection()
    if roadmap_id:
        rows = conn.execute(
            "SELECT * FROM topics WHERE user_id=? AND roadmap_id=? ORDER BY order_idx",
            (user_id, roadmap_id)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM topics WHERE user_id=? ORDER BY order_idx",
            (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_topic_status(topic_id, status, mastery_pct=None):
    conn = get_connection()
    if mastery_pct is not None:
        conn.execute("UPDATE topics SET status=?, mastery_pct=? WHERE id=?",
                     (status, mastery_pct, topic_id))
    else:
        conn.execute("UPDATE topics SET status=? WHERE id=?", (status, topic_id))
    conn.commit()
    conn.close()


# ─── STUDY SESSIONS ──────────────────────────────────────
def log_study_session(user_id, topic_id, topic_name, duration_mins):
    xp = max(5, int(duration_mins * 2))
    conn = get_connection()
    conn.execute("""INSERT INTO study_sessions (user_id, topic_id, topic_name, duration_mins, xp_earned)
                    VALUES (?, ?, ?, ?, ?)""",
                 (user_id, topic_id, topic_name, duration_mins, xp))
    conn.commit()
    conn.close()
    _upsert_daily(user_id, study_mins=duration_mins, xp=xp)
    return xp


def get_study_sessions(user_id, limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM study_sessions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── QUIZ ────────────────────────────────────────────────
def log_quiz_attempt(user_id, topic_id, topic_name, score, total, answers, time_secs):
    pct = round(score / total * 100, 1) if total > 0 else 0
    xp = int(pct / 10) * 5
    conn = get_connection()
    conn.execute("""INSERT INTO quiz_attempts
                    (user_id, topic_id, topic_name, score, total, percentage, answers_json, time_taken_secs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                 (user_id, topic_id, topic_name, score, total, pct,
                  json.dumps(answers), time_secs))
    conn.commit()
    conn.close()
    _upsert_daily(user_id, quiz_accuracy=pct, xp=xp)
    return pct, xp


def get_quiz_attempts(user_id, limit=100):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM quiz_attempts WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── CODE SUBMISSIONS ────────────────────────────────────
def log_code_submission(user_id, topic_id, topic_name, problem_title, code, output, feedback, status):
    xp = 20 if status == "correct" else 5
    conn = get_connection()
    conn.execute("""INSERT INTO code_submissions
                    (user_id, topic_id, topic_name, problem_title, code, output, feedback_json, status, xp_earned)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                 (user_id, topic_id, topic_name, problem_title, code, output,
                  json.dumps(feedback), status, xp))
    conn.commit()
    conn.close()
    _upsert_daily(user_id, xp=xp)
    return xp


def get_code_submissions(user_id, limit=50):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM code_submissions WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── INTERVIEW ───────────────────────────────────────────
def log_interview_session(user_id, topic, job_role, questions, responses, score, feedback):
    conn = get_connection()
    conn.execute("""INSERT INTO interview_sessions
                    (user_id, topic, job_role, questions_json, responses_json, score, feedback)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                 (user_id, topic, job_role, json.dumps(questions), json.dumps(responses), score, feedback))
    conn.commit()
    conn.close()


def get_interview_sessions(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM interview_sessions WHERE user_id=? ORDER BY created_at DESC",
        (user_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["questions_json"] = json.loads(d["questions_json"] or "[]")
        d["responses_json"] = json.loads(d["responses_json"] or "[]")
        result.append(d)
    return result


# ─── PERFORMANCE DAILY ───────────────────────────────────
def _upsert_daily(user_id, study_mins=0, quiz_accuracy=0, xp=0, topics_completed=0):
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM performance_daily WHERE user_id=? AND date=?",
        (user_id, today)).fetchone()
    if row:
        conn.execute("""UPDATE performance_daily
                        SET xp_earned=xp_earned+?, study_mins=study_mins+?,
                            quiz_accuracy=MAX(quiz_accuracy,?),
                            topics_completed=topics_completed+?
                        WHERE user_id=? AND date=?""",
                     (xp, study_mins, quiz_accuracy, topics_completed, user_id, today))
    else:
        # calculate streak
        yesterday = conn.execute(
            "SELECT streak_day FROM performance_daily WHERE user_id=? ORDER BY date DESC LIMIT 1",
            (user_id,)).fetchone()
        streak = (yesterday["streak_day"] + 1) if yesterday else 1
        conn.execute("""INSERT INTO performance_daily
                        (user_id, date, xp_earned, study_mins, quiz_accuracy, topics_completed, streak_day)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (user_id, today, xp, study_mins, quiz_accuracy, topics_completed, streak))
    conn.commit()
    conn.close()


def get_performance_data(user_id, days=30):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM performance_daily WHERE user_id=?
           ORDER BY date DESC LIMIT ?""",
        (user_id, days)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_total_stats(user_id):
    conn = get_connection()
    xp = conn.execute("SELECT COALESCE(SUM(xp_earned),0) FROM performance_daily WHERE user_id=?",
                       (user_id,)).fetchone()[0]
    study = conn.execute("SELECT COALESCE(SUM(duration_mins),0) FROM study_sessions WHERE user_id=?",
                          (user_id,)).fetchone()[0]
    quizzes = conn.execute("SELECT COUNT(*) FROM quiz_attempts WHERE user_id=?",
                            (user_id,)).fetchone()[0]
    streak = conn.execute(
        "SELECT COALESCE(MAX(streak_day),0) FROM performance_daily WHERE user_id=?",
        (user_id,)).fetchone()[0]
    code_solved = conn.execute(
        "SELECT COUNT(*) FROM code_submissions WHERE user_id=? AND status='correct'",
        (user_id,)).fetchone()[0]
    conn.close()
    return {"total_xp": xp, "total_study_mins": study,
            "quizzes_taken": quizzes, "max_streak": streak,
            "code_solved": code_solved}
