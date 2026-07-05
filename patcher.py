import re
import requests
import os

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def apply_patch(file_path,new_code):

    with open(file_path,"w",encoding="utf-8") as file:
        file.writelines(new_code)

def ask_llm(broken_code, error_output, model=None):
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not set. Set it as an environment variable.")
        return ""

    selected_model = model or GROQ_MODEL
    short_error = error_output[:200]
    prompt = (
        "Fix this Python code. Return ONLY corrected code in ```python blocks. No explanation.\n\n"
        "Code:\n"
        f"{broken_code}\n\n"
        "Error:\n"
        f"{short_error}\n"
    )

    response = requests.post(
        GROQ_API_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": selected_model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }
    )

    data = response.json()
    if "error" in data:
        print(f"Groq error: {data['error']}")
        return ""

    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"Unexpected Groq response format: {data}")
        return ""

def extract_code(llm_response):
    match = re.search(r"```python\n(.*?)```",llm_response,re.DOTALL)
    if match:
        return match.group(1).strip()
    else:
        return None