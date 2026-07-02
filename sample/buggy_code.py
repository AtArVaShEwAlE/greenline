def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b

def is_palindrome(s: str) -> bool:
    if len(s) <= 1:
        return True
    return s == s[::-1]