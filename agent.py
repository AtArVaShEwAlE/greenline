from runner import run_tests, find_failing_files
from patcher import ask_llm, extract_code, apply_patch
from vcs import git_commit
import difflib
import os

def show_diff(original_code, fixed_code, log_callback=print):
    original_lines = original_code.splitlines()
    fixed_lines = fixed_code.splitlines()

    diff = list(difflib.unified_diff(
        original_lines, fixed_lines, fromfile="before", tofile="after", lineterm=""
    ))

    if not diff:
        log_callback("ℹ️ No changes detected.")
        return

    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            log_callback(f"DIFF:HEADER:{line}")
        elif line.startswith("-"):
            log_callback(f"DIFF:REMOVED:{line[1:]}")
        elif line.startswith("+"):
            log_callback(f"DIFF:ADDED:{line[1:]}")

def run_agent(project_dir, test_target, max_retries=5, model=None, log_callback=print):
    """
    project_dir: folder containing the source .py files to heal
    test_target: file or folder pytest should run
    """
    for attempt in range(1, max_retries + 1):
        result = run_tests(test_target)

        if result["passed"]:
            log_callback("✅ All tests passed!")
            return {"success": True, "attempts": attempt}

        failed = result["output"].count("FAILED")
        log_callback(f"⏳ Attempt {attempt} — {failed} test(s) failing.")

        failing_files = find_failing_files(result["output"], project_dir)

        if not failing_files:
            log_callback("⚠️ Couldn't identify which file is failing. Stopping.")
            return {"success": False, "attempts": attempt}

        log_callback(f"🔎 Implicated file(s): {', '.join(os.path.basename(f) for f in failing_files)}")

        # Heal one implicated file per attempt (simplest, most controllable approach)
        code_file = failing_files[0]

        with open(code_file, "r", encoding="utf-8") as f:
            current_code = f.read()

        log_callback(f"ACTIVEFILE:{code_file}")
        log_callback(f"🧠 Asking AI to fix {os.path.basename(code_file)}...")
        llm_reply = ask_llm(current_code, result["output"], model=model)
        fixed_code = extract_code(llm_reply)

        if not fixed_code:
            log_callback("⚠️ AI couldn't generate a fix. Retrying...")
            continue

        show_diff(current_code, fixed_code, log_callback)
        apply_patch(code_file, fixed_code)
        log_callback(f"🔧 Patch applied to {os.path.basename(code_file)}.")

        repo_dir = os.path.dirname(os.path.abspath(code_file)) or "."
        commit_msg = f"Greenline: auto-fix attempt {attempt} ({os.path.basename(code_file)})"
        committed = git_commit(repo_dir, commit_msg)
        if committed:
            log_callback(f"📌 Committed: \"{commit_msg}\"")
        else:
            log_callback("⚠️ Git commit skipped (no repo or nothing changed).")

    log_callback(f"❌ Greenline gave up after {max_retries} attempts.")
    return {"success": False, "attempts": max_retries}

if __name__ == "__main__":
    run_agent("sample", "sample")