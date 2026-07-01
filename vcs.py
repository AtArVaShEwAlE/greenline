import subprocess

def git_commit(repo_dir, message):
    """
    Stages all changes and commits them.
    Returns True on success, False if git isn't available or the commit fails
    (e.g. nothing to commit).
    """
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=repo_dir,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False