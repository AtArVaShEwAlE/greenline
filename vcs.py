import subprocess

def git_commit(repo_dir, message):
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_dir, capture_output=True, text=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
    
def get_commit_history(repo_dir, file_path, limit=20):
    """
    Returns a list of dicts: [{"hash": ..., "message": ..., "date": ...}, ...]
    ordered newest first, for commits that touched this specific file.
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-{limit}", "--pretty=format:%h|%ad|%s",
             "--date=short", "--", file_path],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        commits = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                commits.append({"hash": parts[0], "date": parts[1], "message": parts[2]})
        return commits
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

def get_file_at_commit(repo_dir, file_path, commit_hash):
    """
    Returns the file's content as it existed at a specific commit, or None on failure.
    file_path should be relative to repo_dir.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{commit_hash}:{file_path}"],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"DEBUG git show failed: {e.stderr}")   # TEMP
        return None
    except FileNotFoundError:
        print("DEBUG git not found")   # TEMP
        return None


def restore_file_from_commit(repo_dir, file_path, commit_hash, absolute_file_path):
    """
    Overwrites the current file with its version from commit_hash,
    then commits this restore as a NEW commit (non-destructive to history).
    Returns True on success.
    """
    content = get_file_at_commit(repo_dir, file_path, commit_hash)
    if content is None:
        return False

    with open(absolute_file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return git_commit(repo_dir, f"Greenline: restored to {commit_hash}")

def get_repo_root(start_dir):
    """Returns the top-level directory of the git repo containing start_dir, or None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start_dir, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None