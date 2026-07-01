import re
import requests
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL","http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL","deepseek-r1:1.5b")


def apply_patch(file_path,new_code):

    with open(file_path,"w") as file:
        file.writelines(new_code)

def ask_llm(broken_code, error_output):
    # Trim error output to just first 200 chars
    short_error = error_output[:200]
    
    prompt = (
        "Fix this Python code. Return ONLY corrected code in ```python blocks. No explanation.\n\n"
        "Code:\n"
        f"{broken_code}\n\n"
        "Error:\n"
        f"{short_error}\n"
    )

    response = requests.post(
        OLLAMA_BASE_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_gpu": 0    # force CPU only, no GPU
            }
        }
    )

    data = response.json()
    if "error" in data:
        print(f"⚠️ Ollama error: {data['error']}")
        return ""
    return data.get("response", "")

def extract_code(llm_response):

    match = re.search(r"```python\n(.*?)```",llm_response,re.DOTALL)

    if match:
        return match.group(1).strip()
    else:
        return None