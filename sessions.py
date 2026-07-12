import json
import os
from datetime import datetime

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),"greenline_session.json")

def save_session(record):
    """
    record should contain: project_dir, test_target, language, model,
    max_retries, success, attempts, files_touched, duration_seconds
    """
    sessions = load_sessions()
    record["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sessions.insert(0,record)
    sessions = sessions[:100]

    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(sessions,f,indent=2)
    except OSError:
        pass

def load_sessions():
    if not os.path.exists(SESSION_FILE):
        return []
    try:
        with open(SESSION_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except (OSError,json.JSONDecodeError):
        return []