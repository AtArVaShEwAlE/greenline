import subprocess

def run_tests(test_file):

    result = subprocess.run(
        ["pytest",test_file,"--tb=short", "-q"],
        capture_output= True,
        text = True,
    )

    return {
        "passed": result.returncode == 0,
        "output": result.stdout + result.stderr,
        "returncode": result.returncode
    }

if __name__ == "__main__":
    result = run_tests("sample/test_code.py")
    print(result)