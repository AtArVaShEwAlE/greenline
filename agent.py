from runner import (
    run_tests, find_failing_files, get_related_files,
    find_failing_files_js, get_related_files_js,
    find_failing_files_unittest,
    detect_project_language, detect_test_framework
)
from patcher import ask_llm, extract_code, extract_explanation_and_confidence, apply_patch
from vcs import git_commit, create_backup_branch, get_repo_root
import difflib
import os
import time

CONFIDENCE_THRESHOLD = 70

def show_diff(original_code, fixed_code, log_callback=print):
    original_lines = original_code.splitlines()
    fixed_lines = fixed_code.splitlines()
    diff = list(difflib.unified_diff(original_lines, fixed_lines, fromfile="before", tofile="after", lineterm=""))
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

def run_agent(project_dir, test_target, max_retries=5, model=None, log_callback=print, approval_callback=None):
    start_time = time.time()
    touched_files = []
    language = detect_project_language(project_dir)
    framework = detect_test_framework(test_target) if language == "python" else "jest"
    log_callback(f"🔤 Detected language: {language}  |  Framework: {framework}")

    repo_root = get_repo_root(project_dir)
    backup_branch = None
    if repo_root:
        backup_branch = create_backup_branch(repo_root)
        if backup_branch:
            log_callback(f"🔖 Backup checkpoint created: {backup_branch}")
        else:
            log_callback("⚠️ Couldn't create backup branch (no commits yet, or git error).")
    else:
        log_callback("⚠️ Not a git repo — skipping backup branch.")
        
    for attempt in range(1, max_retries + 1):
        result = run_tests(test_target, project_dir=project_dir, language=language, framework=framework)

        if result["passed"]:
            log_callback("✅ All tests passed!")
            return {
                "success": True, "attempts": attempt, "files_touched": touched_files,
                "duration_seconds": round(time.time() - start_time, 1), "language": language,
                "backup_branch": backup_branch
            }

        if language == "javascript":
            marker = "✕"
        elif framework == "unittest":
            marker = "FAIL:"
        else:
            marker = "FAILED"
        failed = result["output"].count(marker)
        log_callback(f"⏳ Attempt {attempt} — {failed} test(s) failing.")

        if language == "javascript":
            failing_files = find_failing_files_js(result["output"], project_dir)
        elif framework == "unittest":
            failing_files = find_failing_files_unittest(result["output"], project_dir, test_target)
        else:
            failing_files = find_failing_files(result["output"], project_dir)

        if not failing_files:
            log_callback("⚠️ Couldn't identify which file is failing. Stopping.")
            return {
                "success": False, "attempts": attempt, "files_touched": touched_files,
                "duration_seconds": round(time.time() - start_time, 1), "language": language,
                "backup_branch": backup_branch
            }

        log_callback(f"🔎 Implicated file(s): {', '.join(os.path.basename(f) for f in failing_files)}")
        code_file = failing_files[0]

        with open(code_file, "r", encoding="utf-8") as f:
            current_code = f.read()

        related_files = get_related_files_js(code_file, project_dir) if language == "javascript" else get_related_files(code_file, project_dir)
        if related_files:
            log_callback(f"📎 Including context from: {', '.join(related_files.keys())}")

        log_callback(f"ACTIVEFILE:{code_file}")
        log_callback(f"🧠 Asking AI to fix {os.path.basename(code_file)}...")
        llm_reply = ask_llm(current_code, result["output"], model=model, related_files=related_files, language=language)
        fixed_code = extract_code(llm_reply, language=language)
        explanation, confidence = extract_explanation_and_confidence(llm_reply)

        if not fixed_code:
            log_callback("⚠️ AI couldn't generate a fix. Retrying...")
            continue

        if explanation:
            log_callback(f"💡 {explanation}")
        log_callback(f"📊 Confidence: {confidence}%")

        if approval_callback:
            log_callback("⏸️ Waiting for your review...")
            approved = approval_callback(current_code, fixed_code, explanation, confidence)
            if not approved:
                log_callback("🚫 Patch rejected. Retrying...")
                continue

        show_diff(current_code, fixed_code, log_callback)
        apply_patch(code_file, fixed_code)
        log_callback(f"🔧 Patch applied to {os.path.basename(code_file)}.")

        file_name = os.path.basename(code_file)
        if file_name not in touched_files:
            touched_files.append(file_name)

        repo_dir = os.path.dirname(os.path.abspath(code_file)) or "."
        commit_msg = f"Greenline: auto-fix attempt {attempt} ({os.path.basename(code_file)})"
        committed = git_commit(repo_dir, commit_msg)
        if committed:
            log_callback(f"📌 Committed: \"{commit_msg}\"")
        else:
            log_callback("⚠️ Git commit skipped (no repo or nothing changed).")

    log_callback(f"❌ Greenline gave up after {max_retries} attempts.")
    return {
        "success": False, "attempts": max_retries, "files_touched": touched_files,
        "duration_seconds": round(time.time() - start_time, 1), "language": language,
        "backup_branch": backup_branch
    }