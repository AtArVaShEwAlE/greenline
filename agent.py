from runner import run_tests
from patcher import ask_llm, extract_code, apply_patch
import difflib
from vcs import git_commit
import os

def show_diff(original_code, fixed_code, log_callback=print):
    original_lines = original_code.splitlines()
    fixed_lines = fixed_code.splitlines()

    diff = list(difflib.unified_diff(
        original_lines,
        fixed_lines,
        fromfile="before",
        tofile="after",
        lineterm=""
    ))

    if not diff:
        log_callback("ℹ️ No changes detected.")
        return

    # send diff lines prefixed with DIFF: so UI can intercept them
    for line in diff:
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            log_callback(f"DIFF:HEADER:{line}")
        elif line.startswith("-"):
            log_callback(f"DIFF:REMOVED:{line[1:]}")
        elif line.startswith("+"):
            log_callback(f"DIFF:ADDED:{line[1:]}")

def run_agent(code_file, test_file, max_retries=5, log_callback=print):
    for attempt in range(1, max_retries + 1):
        result = run_tests(test_file)

        if result["passed"]:
            log_callback("✅ All tests passed!")
            return {"success": True, "attempts": attempt}   # ← changed

        failed = result["output"].count("FAILED")
        log_callback(f"⏳ Attempt {attempt} — {failed} test(s) failing. Asking AI for fix...")

        with open(code_file, "r") as f:
            current_code = f.read()

        llm_reply = ask_llm(current_code, result["output"])
        fixed_code = extract_code(llm_reply)

        if not fixed_code:
            log_callback("⚠️ AI couldn't generate a fix. Retrying...")
            continue

        show_diff(current_code, fixed_code, log_callback)
        apply_patch(code_file, fixed_code)
        log_callback("🔧 Patch applied.")

        repo_dir = os.path.dirname(os.path.abspath(code_file)) or "."
        commit_msg = f"Greenline: auto-fix attempt {attempt}"
        committed = git_commit(repo_dir, commit_msg)
        if committed:
            log_callback(f"📌 Committed: \"{commit_msg}\"")
        else:
            log_callback("⚠️ Git commit skipped (no repo or nothing changed).")

    log_callback(f"❌ Greenline gave up after {max_retries} attempts.")
    return {"success": False, "attempts": max_retries}   # ← changed

if __name__ == "__main__":
    run_agent("sample/buggy_code.py", "sample/test_code.py")