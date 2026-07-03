class Calculator:
    def __init__(self):
        self.history = []

    def add(self, a, b):
        result = a + b  
        self.history.append(result)
        return result

    def divide(self, a, b):
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        result = a / b  
        self.history.append(result)
        return result

    def average(self, numbers):
        total = 0
        for n in numbers:
            total += n
        return total / len(numbers)  

    def is_even(self, n):
        return n % 2 == 0  

    def factorial(self, n):
        if n == 0:
            return 1
        result = 1
        for i in range(1, n + 1):  
            result *= i
        return result

    def find_max(self, numbers):
        max_val = numbers[0]  
        for n in numbers:
            if n > max_val:
                max_val = n
        return max_val