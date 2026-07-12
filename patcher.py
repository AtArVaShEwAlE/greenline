import re
import requests
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

call_count = 0

def apply_patch(file_path, new_code):
    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(new_code)

def ask_llm(broken_code, error_output, model=None, related_files=None, language="python"):
    if not GROQ_API_KEY:
        print("⚠️ GROQ_API_KEY not set. Set it as an environment variable.")
        return ""

    selected_model = model or GROQ_MODEL
    short_error = error_output[:400]

    context_block = ""
    if related_files:
        for fname, content in related_files.items():
            context_block += f"\n--- Related file: {fname} ---\n{content}\n"

    prompt = (
        f"You are fixing a bug in a {language.upper()} project. Below is the broken file, "
        "the test failure output, and related files it depends on for context.\n\n"
        "Respond in EXACTLY this format, nothing else:\n"
        "EXPLANATION: <one or two sentence explanation of the root cause>\n"
        "CONFIDENCE: <integer 0-100, how confident you are this fix is fully correct>\n"
        f"```{language}\n<the complete corrected file content>\n```\n\n"
        "Broken file:\n"
        f"{broken_code}\n\n"
        "Test failure output:\n"
        f"{short_error}\n"
        f"{context_block}"
    )

    try:
        response = requests.post(
            GROQ_API_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": selected_model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2},
            timeout=30
        )
    except requests.exceptions.Timeout:
        print("⚠️ Groq API timed out after 30 seconds. Try again shortly.")
        return ""
    except requests.exceptions.ConnectionError:
        print("⚠️ Couldn't reach Groq API. Check your internet connection.")
        return ""

    if response.status_code == 429:
        print("⚠️ Groq rate limit hit. Wait a bit before trying again.")
        return ""

    data = response.json()
    if "error" in data:
        print(f"⚠️ Groq error: {data['error']}")
        return ""

    try:
        global call_count
        call_count += 1
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"⚠️ Unexpected Groq response format: {data}")
        return ""
    

def extract_code(llm_response, language="python"):
    match = re.search(rf"```{re.escape(language)}\n(.*?)```", llm_response, re.DOTALL)
    if match:
        return match.group(1).strip()
    # fallback: accept any code fence in case the model used a slightly different label
    match = re.search(r"```\w*\n(.*?)```", llm_response, re.DOTALL)
    return match.group(1).strip() if match else None

def extract_explanation_and_confidence(llm_response):
    explanation = ""
    confidence = 50

    exp_match = re.search(r"EXPLANATION:\s*(.+?)(?:\s*CONFIDENCE:|\n|$)", llm_response, re.DOTALL)
    if exp_match:
        explanation = exp_match.group(1).strip()

    conf_match = re.search(r"CONFIDENCE:\s*(\d+)", llm_response)
    if conf_match:
        confidence = max(0, min(100, int(conf_match.group(1))))

    return explanation, confidence

def get_call_count():
    return call_count