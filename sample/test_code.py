import pytest
from buggy_code import Calculator

@pytest.fixture
def calc():
    return Calculator()

def test_add(calc):
    assert calc.add(2, 3) == 5

def test_divide(calc):
    assert calc.divide(10, 2) == 5

def test_average(calc):
    assert calc.average([2, 4, 6]) == 4

def test_is_even(calc):
    assert calc.is_even(4) is True
    assert calc.is_even(3) is False

def test_factorial(calc):
    assert calc.factorial(5) == 120

def test_find_max_with_negatives(calc):
    assert calc.find_max([-5, -2, -10]) == -2