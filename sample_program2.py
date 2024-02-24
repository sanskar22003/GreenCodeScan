# sample_program.py

def fibonacci(n):
    if n <= 0:
        return []
    elif n == 1:
        return [0]
    elif n == 2:
        return [0, 1]
    else:
        fib_sequence = [0, 1]
        while len(fib_sequence) < n:
            fib_sequence.append(fib_sequence[-1] + fib_sequence[-2])
        return fib_sequence
    
if __name__ == "__main__":
    n = int(input("Enter the number of Fibonacci numbers to generate: "))
    print(f"Fibonacci sequence of {n} numbers:", fibonacci(n))
