"""
search_analysis.py
==================
Module 1: Search Algorithm Analysis (Linear Search and Binary Search).

Both search functions are written by hand (no list.index(), no bisect, no `in`)
and both COUNT how many comparisons they make.

Run this file directly for a quick demo:   python search_analysis.py
"""

import random

import pandas as pd

from benchmark_engine import BenchmarkEngine, measure_function, save_csv

DEFAULT_SEARCH_SIZES = [100, 1000, 10000, 50000]   # sizes suggested in the assignment
MAX_DATASET_SIZE = 1_000_000                        # safety limit for the app
SEARCH_ALGORITHMS = ["Linear Search", "Binary Search"]


# ---------------------------------------------------------------------------
# Dataset generation
# ---------------------------------------------------------------------------
def validate_size(n):
    """Dataset size must be a whole number between 0 and MAX_DATASET_SIZE."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("Dataset size must be a whole number.")
    if n < 0:
        raise ValueError("Dataset size cannot be negative.")
    if n > MAX_DATASET_SIZE:
        raise ValueError(f"Dataset size is too large (maximum {MAX_DATASET_SIZE:,}).")


def generate_sorted_dataset(n):
    """Sorted list of n even numbers: [0, 2, 4, ..., 2(n-1)].
    Even numbers only, so any odd key is guaranteed to be 'not found'."""
    validate_size(n)
    return [2 * i for i in range(n)]


def generate_unsorted_dataset(n, seed=42):
    """List of n random numbers between 0 and 2n (NOT sorted). Same seed -> same list."""
    validate_size(n)
    rng = random.Random(seed)
    return [rng.randint(0, 2 * n) for _ in range(n)]


def is_sorted(data):
    """True if data is in ascending order (checked by hand, O(n))."""
    for i in range(1, len(data)):
        if data[i - 1] > data[i]:
            return False
    return True


def worst_case_key(n):
    """A key that is NOT in generate_sorted_dataset(n) and is larger than
    every element, which forces both algorithms to do their maximum work."""
    return 2 * n - 1


# ---------------------------------------------------------------------------
# The two search algorithms
# ---------------------------------------------------------------------------
def linear_search(data, key):
    """
    Check every element from left to right.
    Returns (index, comparisons); index is -1 if the key is not found.
    Each element-versus-key check counts as 1 comparison.
    """
    comparisons = 0
    for index in range(len(data)):
        comparisons += 1
        if data[index] == key:
            return index, comparisons
    return -1, comparisons


def binary_search(data, key):
    """
    Repeatedly halve the search range. `data` MUST be sorted (ascending).
    Returns (index, comparisons); index is -1 if the key is not found.
    Each look at the middle element (compared with the key) counts as 1 comparison.
    """
    low, high = 0, len(data) - 1
    comparisons = 0
    while low <= high:
        middle = (low + high) // 2
        comparisons += 1
        if data[middle] == key:
            return middle, comparisons
        if data[middle] < key:
            low = middle + 1
        else:
            high = middle - 1
    return -1, comparisons


SEARCH_FUNCTIONS = {"Linear Search": linear_search, "Binary Search": binary_search}


# ---------------------------------------------------------------------------
# Running one search (used by the Streamlit app)
# ---------------------------------------------------------------------------
def run_search(algorithm, n, key, sorted_data=True, repeats=5):
    """
    Build a dataset of size n, run the chosen search, and measure it.

    Returns a dictionary with: algorithm, input_size, key, found, index,
    comparisons, execution_time (seconds), memory_usage (KB).
    Raises ValueError for invalid input (unknown algorithm, bad size/key,
    or Binary Search on unsorted data).
    """
    if algorithm not in SEARCH_FUNCTIONS:
        raise ValueError(f"Unknown algorithm '{algorithm}'. Choose from {SEARCH_ALGORITHMS}.")
    validate_size(n)
    if isinstance(key, bool) or not isinstance(key, int):
        raise ValueError("Search key must be a whole number.")

    data = generate_sorted_dataset(n) if sorted_data else generate_unsorted_dataset(n)

    if algorithm == "Binary Search" and not is_sorted(data):
        raise ValueError("Binary Search only works on sorted data. Choose a sorted dataset.")

    (index, comparisons), seconds, memory_kb = measure_function(
        SEARCH_FUNCTIONS[algorithm], (data, key), repeats)

    return {
        "algorithm": algorithm,
        "input_size": n,
        "key": key,
        "found": index != -1,
        "index": index,
        "comparisons": comparisons,
        "operations": comparisons,
        "execution_time": seconds,
        "memory_usage": memory_kb,
        "data_preview": data[:10],
    }


# ---------------------------------------------------------------------------
# Automated benchmark (uses BenchmarkEngine)
# ---------------------------------------------------------------------------
def run_search_benchmark(sizes=None, repeats=5, save=False):
    """
    Benchmark both search algorithms on sorted datasets of several sizes,
    always searching for a key that is NOT present (worst case).
    Returns a DataFrame with algorithm, input_size, execution_time,
    memory_usage, comparisons, status. If save=True also writes
    results/search_benchmark.csv.
    """
    sizes = sizes or DEFAULT_SEARCH_SIZES
    engine = BenchmarkEngine(repeats=repeats)

    def setup(n):
        return generate_sorted_dataset(n), worst_case_key(n)

    def extras(result):
        return {"operations": result[1], "comparisons": result[1]}

    for name in SEARCH_ALGORITHMS:
        engine.run(name, SEARCH_FUNCTIONS[name], sizes, setup=setup, extras=extras)

    df = engine.get_dataframe()
    if save:
        save_csv(df, "search_benchmark.csv")
    return df


if __name__ == "__main__":
    print("=== Quick demo: Search Algorithm Analysis ===")
    demo = generate_sorted_dataset(1000)
    for algo in SEARCH_ALGORITHMS:
        info = run_search(algo, 1000, 500)
        print(f"{algo}: found={info['found']}, index={info['index']}, "
              f"comparisons={info['comparisons']}, time={info['execution_time']:.8f} s, "
              f"memory={info['memory_usage']:.3f} KB")

    print("\nKey not present (worst case):")
    print(run_search("Binary Search", 1000, 501)["found"])

    print("\nBinary Search on unsorted data:")
    try:
        run_search("Binary Search", 1000, 5, sorted_data=False)
    except ValueError as error:
        print("Error caught ->", error)

    print("\nBenchmark results:")
    print(run_search_benchmark(save=True).to_string(index=False))
