import json
import os

SETTINGS_FILE = "greenline_settings.json"

DEFAULT_SETTINGS = {
    "model": "llama-3.3-70b-versatile",
    "max_retries": 5,
    "last_project_dir": None,
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            settings = DEFAULT_SETTINGS.copy()
            settings.update(data)
            return settings
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass

PROJECT_SETTINGS_FILENAME = ".greenline.json"

def load_project_settings(project_dir):
    path = os.path.join(project_dir, PROJECT_SETTINGS_FILENAME)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    return None

def save_project_settings(project_dir, settings):
    path = os.path.join(project_dir, PROJECT_SETTINGS_FILENAME)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError:
        pass