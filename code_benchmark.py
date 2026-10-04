"""
code_benchmark.py
=================
Module 2: Code Benchmarking - four small programs:
  1. Single Loop Traversal
  2. Nested Loop Traversal
  3. Recursive Factorial
  4. Iterative Factorial

Run this file directly for a quick demo:   python code_benchmark.py
"""

import math
import sys
from contextlib import contextmanager

import pandas as pd

from benchmark_engine import BenchmarkEngine, measure_function, save_csv

DEFAULT_LOOP_SIZES = [100, 1000, 10000, 50000]   # sizes suggested in the assignment
DEFAULT_FACTORIAL_SIZES = [100, 500, 1000]       # sizes suggested in the assignment

# The nested loop does n*n steps, so n = 50000 means 2.5 BILLION steps in Python.
# Memory measurement (tracemalloc) makes every step much slower, so n = 10000
# already takes over a minute and n = 50000 would take hours.
# In automated benchmarks, sizes above this limit are recorded as "skipped"
# unless include_slow=True is used.
NESTED_LOOP_SAFE_LIMIT = 2000

# Largest input each program accepts in the interactive app
MAX_INPUT = {
    "Single Loop": 1_000_000,
    "Nested Loop": 3000,     # n*n steps - larger values take too long
    "Recursive Factorial": 2000,    # limited by Python's recursion depth
    "Iterative Factorial": 10000,
}


# ---------------------------------------------------------------------------
# The four programs
# ---------------------------------------------------------------------------
def single_loop(n):
    """Add up the numbers 0..n-1 with ONE loop. Time O(n), space O(1)."""
    total = 0
    for i in range(n):
        total += i
    return total


def nested_loop(n):
    """Count the steps of a loop inside a loop. Returns n*n. Time O(n²), space O(1)."""
    count = 0
    for i in range(n):
        for j in range(n):
            count += 1
    return count


def iterative_factorial(n):
    """n! using a loop. Time O(n), space O(1) (extra memory, apart from the result)."""
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def _factorial_recursive_step(n, depth, stats):
    """Helper: n! by recursion. `stats` remembers the deepest level reached."""
    if depth > stats["max_depth"]:
        stats["max_depth"] = depth
    if n <= 1:
        return 1
    return n * _factorial_recursive_step(n - 1, depth + 1, stats)


@contextmanager
def _temporary_recursion_limit(needed):
    """Raise Python's recursion limit while the block runs, then restore it."""
    old_limit = sys.getrecursionlimit()
    if needed > old_limit:
        sys.setrecursionlimit(needed)
    try:
        yield
    finally:
        sys.setrecursionlimit(old_limit)


def recursive_factorial_with_depth(n):
    """
    n! using recursion. Time O(n), space O(n) (one stack frame per call).
    Returns (result, max_recursion_depth). The recursion limit is raised
    temporarily so that n up to MAX_INPUT["Recursive Factorial"] works.
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    if n > MAX_INPUT["Recursive Factorial"]:
        raise ValueError(
            f"n is too large for recursion (maximum {MAX_INPUT['Recursive Factorial']}). "
            "Use Iterative Factorial for bigger values.")
    stats = {"max_depth": 0}
    with _temporary_recursion_limit(n + 100):
        result = _factorial_recursive_step(n, 1, stats)
    return result, stats["max_depth"]


def recursive_factorial(n):
    """n! using recursion (returns only the result)."""
    return recursive_factorial_with_depth(n)[0]


# ---------------------------------------------------------------------------
# Running one program (used by the Streamlit app)
# ---------------------------------------------------------------------------
PROGRAM_FUNCTIONS = {
    "Single Loop": single_loop,
    "Nested Loop": nested_loop,
    "Recursive Factorial": recursive_factorial_with_depth,
    "Iterative Factorial": iterative_factorial,
}
PROGRAM_NAMES = list(PROGRAM_FUNCTIONS)


def validate_program_input(program, n):
    """Raise ValueError if the program name or input value is not acceptable."""
    if program not in PROGRAM_FUNCTIONS:
        raise ValueError(f"Unknown program '{program}'. Choose from {PROGRAM_NAMES}.")
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("Input must be a whole number.")
    if n < 0:
        raise ValueError("Input cannot be negative.")
    if n > MAX_INPUT[program]:
        raise ValueError(f"Input is too large for {program} (maximum {MAX_INPUT[program]:,}).")


def format_big_number(value):
    """Show huge factorials in a short form (also avoids Python's int-to-text digit limit)."""
    if value.bit_length() <= 64:
        return str(value)
    log_value = math.log10(value)
    exponent = int(log_value)
    mantissa = 10 ** (log_value - exponent)
    return f"{mantissa:.4f} x 10^{exponent}  (about {exponent + 1} digits)"


def run_program(program, n):
    """
    Run one of the four programs with input n and measure it.
    Returns a dictionary: program, input_size, result (readable text),
    execution_time (seconds), memory_usage (KB), max_recursion_depth (or None).
    """
    validate_program_input(program, n)
    repeats = 1 if program == "Nested Loop" else 3     # nested loop can be slow

    raw, seconds, memory_kb = measure_function(PROGRAM_FUNCTIONS[program], (n,), repeats)

    depth = None
    if program == "Recursive Factorial":
        raw, depth = raw
    return {
        "program": program,
        "input_size": n,
        "result": format_big_number(raw),
        "execution_time": seconds,
        "memory_usage": memory_kb,
        "max_recursion_depth": depth,
    }


# ---------------------------------------------------------------------------
# Automated benchmarks (use BenchmarkEngine)
# ---------------------------------------------------------------------------
def run_loop_benchmark(sizes=None, include_slow=False, save=False):
    """
    Benchmark Single Loop and Nested Loop.
    Nested Loop sizes above NESTED_LOOP_SAFE_LIMIT are recorded as "skipped"
    unless include_slow=True (n = 10000 takes over a minute, n = 50000 hours).
    """
    sizes = sizes or DEFAULT_LOOP_SIZES
    engine = BenchmarkEngine(repeats=3)
    engine.run("Single Loop", single_loop, sizes)
    engine.run("Nested Loop", nested_loop, sizes, repeats=1,
               max_size=None if include_slow else NESTED_LOOP_SAFE_LIMIT)
    df = engine.get_dataframe()
    if save:
        save_csv(df, "loop_benchmark.csv")
    return df


def run_factorial_benchmark(sizes=None, save=False):
    """Benchmark Recursive Factorial and Iterative Factorial."""
    sizes = sizes or DEFAULT_FACTORIAL_SIZES
    engine = BenchmarkEngine(repeats=5)
    engine.run("Recursive Factorial", recursive_factorial_with_depth, sizes,
               extras=lambda result: {"max_recursion_depth": result[1]})
    engine.run("Iterative Factorial", iterative_factorial, sizes)
    df = engine.get_dataframe()
    if save:
        save_csv(df, "factorial_benchmark.csv")
    return df


if __name__ == "__main__":
    print("=== Quick demo: Code Benchmarking ===")
    for program, value in [("Single Loop", 1000), ("Nested Loop", 100),
                           ("Recursive Factorial", 10), ("Iterative Factorial", 10)]:
        info = run_program(program, value)
        print(f"{program}(n={value}): result={info['result']}, "
              f"time={info['execution_time']:.8f} s, memory={info['memory_usage']:.3f} KB")

    print("\nEdge cases:")
    print("0! =", iterative_factorial(0), "| 1! =", recursive_factorial(1))
    try:
        run_program("Iterative Factorial", -5)
    except ValueError as error:
        print("Error caught ->", error)

    print("\nLoop benchmark:")
    print(run_loop_benchmark(save=True).to_string(index=False))
    print("\nFactorial benchmark:")
    print(run_factorial_benchmark(save=True).to_string(index=False))
