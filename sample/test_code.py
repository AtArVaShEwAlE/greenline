from buggy_code import add, multiply, is_palindrome

def test_add():
    assert add(2, 3) == 5

def test_multiply():
    assert multiply(3, 4) == 12

def test_palindrome():
    assert is_palindrome("racecar") == True
    assert is_palindrome("hello") == False