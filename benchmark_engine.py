"""
benchmark_engine.py
===================
Reusable tools for measuring and comparing algorithm performance.

This file does NOT know about any specific algorithm. It only knows how to:
  1. run any function for several input sizes,
  2. measure execution time and memory usage,
  3. store the results in a pandas DataFrame / CSV file,
  4. draw graphs from those results,
  5. summarise the results (experimental growth vs theoretical complexity).

search_analysis.py and code_benchmark.py import from this file.
"""

import math
import time
import tracemalloc
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # "Agg" saves graphs to files without opening a window
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Folders (always relative to this file, so the project works from any folder)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
GRAPHS_DIR = BASE_DIR / "graphs"
RESULTS_DIR = BASE_DIR / "results"

# Column order used in every results table
BASE_COLUMNS = ["algorithm", "input_size", "execution_time", "memory_usage"]

# ---------------------------------------------------------------------------
# Theoretical complexity (from the assignment)
# ---------------------------------------------------------------------------
THEORETICAL_COMPLEXITY = {
    "Linear Search": {"best": "O(1)", "average": "O(n)", "worst": "O(n)", "space": "O(1)", "time_class": "linear"},
    "Binary Search": {"best": "O(1)", "average": "O(log n)", "worst": "O(log n)", "space": "O(1)", "time_class": "log"},
    "Single Loop": {"best": "O(n)", "average": "O(n)", "worst": "O(n)", "space": "O(1)", "time_class": "linear"},
    "Nested Loop": {"best": "O(n²)", "average": "O(n²)", "worst": "O(n²)", "space": "O(1)", "time_class": "quadratic"},
    "Recursive Factorial": {"best": "O(n)", "average": "O(n)", "worst": "O(n)", "space": "O(n)", "time_class": "linear"},
    "Iterative Factorial": {"best": "O(n)", "average": "O(n)", "worst": "O(n)", "space": "O(1)", "time_class": "linear"},
}


# ---------------------------------------------------------------------------
# Measuring ONE run
# ---------------------------------------------------------------------------
def measure_function(func, args=(), repeats=3):
    """
    Run func(*args) and measure its time and memory.

    Time and memory are measured in SEPARATE runs, because tracemalloc slows a
    program down and would make the timing wrong.

    Returns (result, average_time_in_seconds, peak_memory_in_KB).
    Memory is the peak EXTRA memory allocated while the function runs.
    (Data prepared before the call, such as the input list, is not counted.)
    """
    if repeats < 1:
        raise ValueError("repeats must be at least 1")

    # 1) Timing run(s) - no tracemalloc active
    times = []
    result = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = func(*args)
        times.append(time.perf_counter() - start)
    average_time = sum(times) / len(times)

    # 2) Memory run - tracemalloc active
    tracemalloc.start()
    try:
        func(*args)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return result, average_time, peak_bytes / 1024


# ---------------------------------------------------------------------------
# The reusable engine
# ---------------------------------------------------------------------------
class BenchmarkEngine:
    """Runs a function for many input sizes and stores the results."""

    def __init__(self, repeats=3):
        self.repeats = repeats
        self.rows = []

    def run(self, algorithm, func, input_sizes, setup=None, extras=None,
            max_size=None, repeats=None):
        """
        Benchmark `func` for every size in `input_sizes`.

        algorithm  : name stored in the results (e.g. "Linear Search")
        func       : the function to test, called as func(*args)
        input_sizes: list of sizes, e.g. [100, 1000, 10000]
        setup      : optional function size -> tuple of arguments for func.
                     Its work is NOT timed (use it to build the dataset).
                     Default: func is called as func(size).
        extras     : optional function result -> dict of extra columns
                     (e.g. {"comparisons": 42}).
        max_size   : sizes above this are NOT run; they are recorded with a
                     "skipped" status (used for very slow programs).
        repeats    : override the engine's default number of timing repeats.

        Returns the results of ALL benchmarks so far as a DataFrame.
        """
        sizes = validate_sizes(input_sizes)
        repeats = repeats or self.repeats

        for size in sizes:
            row = {"algorithm": algorithm, "input_size": size}

            if max_size is not None and size > max_size:
                row.update(execution_time=np.nan, memory_usage=np.nan,
                           status=f"skipped: size above limit {max_size}")
                self.rows.append(row)
                continue

            try:
                args = setup(size) if setup else (size,)
                result, seconds, memory_kb = measure_function(func, args, repeats)
                row.update(execution_time=seconds, memory_usage=memory_kb, status="ok")
                if extras:
                    row.update(extras(result))
            except (RecursionError, MemoryError, ValueError, OverflowError) as error:
                # The failure is recorded - nothing is invented.
                row.update(execution_time=np.nan, memory_usage=np.nan,
                           status=f"failed: {type(error).__name__}: {error}")
            self.rows.append(row)

        return self.get_dataframe()

    def get_dataframe(self):
        """All stored results as a pandas DataFrame."""
        if not self.rows:
            return pd.DataFrame(columns=BASE_COLUMNS + ["status"])
        df = pd.DataFrame(self.rows)
        first = BASE_COLUMNS
        last = ["status"]
        middle = [c for c in df.columns if c not in first + last]
        return df[first + middle + last]

    def clear(self):
        """Forget all stored results."""
        self.rows = []

    def save_csv(self, filename):
        """Save the stored results to results/<filename>. Returns the path."""
        return save_csv(self.get_dataframe(), filename)


def validate_sizes(input_sizes):
    """Check that input_sizes is a non-empty list of non-negative integers."""
    sizes = list(input_sizes)
    if not sizes:
        raise ValueError("Please provide at least one input size.")
    for size in sizes:
        if isinstance(size, bool) or not isinstance(size, (int, np.integer)):
            raise ValueError(f"Input size must be a whole number, got {size!r}.")
        if size < 0:
            raise ValueError(f"Input size cannot be negative, got {size}.")
    return [int(s) for s in sizes]


def save_csv(df, filename):
    """Save a DataFrame as results/<filename> (folder is created if needed)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / filename
    df.to_csv(path, index=False)
    return path


# ---------------------------------------------------------------------------
# Formatting helpers (used by the Streamlit app and the notebook)
# ---------------------------------------------------------------------------
def format_time(seconds):
    """Turn seconds into a readable string (µs, ms or s)."""
    if seconds is None or (isinstance(seconds, float) and math.isnan(seconds)):
        return "n/a"
    if seconds < 1e-3:
        return f"{seconds * 1e6:.2f} µs"
    if seconds < 1:
        return f"{seconds * 1e3:.3f} ms"
    return f"{seconds:.3f} s"


def format_memory(kb):
    """Turn kilobytes into a readable string (KB or MB)."""
    if kb is None or (isinstance(kb, float) and math.isnan(kb)):
        return "n/a"
    if kb >= 1024:
        return f"{kb / 1024:.2f} MB"
    return f"{kb:.2f} KB"


# ---------------------------------------------------------------------------
# Graphs (always drawn from a results DataFrame)
# ---------------------------------------------------------------------------
def plot_comparison(df, y_column, title, xlabel, ylabel, filename, y_scale=1.0):
    """
    Draw one line per algorithm (x = input_size, y = y_column) and save it as
    graphs/<filename>. Only rows with status "ok" are plotted.
    Returns the path of the PNG file.
    """
    if df is None or df.empty:
        raise ValueError("There are no results to plot. Run the benchmark first.")
    good = df[(df["status"] == "ok") & df[y_column].notna()]
    if good.empty:
        raise ValueError(f"No successful results with '{y_column}' to plot.")

    fig, ax = plt.subplots(figsize=(8, 5))
    for name, group in good.groupby("algorithm", sort=False):
        group = group.sort_values("input_size")
        ax.plot(group["input_size"], group[y_column] * y_scale, marker="o", label=name)

    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()

    GRAPHS_DIR.mkdir(parents=True, exist_ok=True)
    path = GRAPHS_DIR / filename
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def generate_all_graphs(search_df=None, factorial_df=None, loop_df=None):
    """
    Create every required graph from the given results DataFrames.
    Any DataFrame that is None/empty is skipped.
    Returns a dict {graph title: path to PNG}.
    """
    graphs = {}

    def add(df, y_col, title, xlabel, ylabel, filename, scale=1.0):
        if df is None or df.empty:
            return
        good = df[(df["status"] == "ok")]
        if y_col not in good.columns or good[y_col].dropna().empty:
            return
        graphs[title] = plot_comparison(df, y_col, title, xlabel, ylabel, filename, scale)

    time_label = "Execution Time (ms)"
    memory_label = "Peak Memory Usage (KB)"

    add(search_df, "execution_time", "Linear Search vs Binary Search: Dataset Size vs Execution Time",
        "Dataset Size (n)", time_label, "search_time.png", 1000)
    add(search_df, "comparisons", "Linear Search vs Binary Search: Dataset Size vs Comparisons",
        "Dataset Size (n)", "Number of Comparisons", "search_comparisons.png")
    add(search_df, "memory_usage", "Linear Search vs Binary Search: Dataset Size vs Memory Usage",
        "Dataset Size (n)", memory_label, "search_memory.png")

    add(factorial_df, "execution_time", "Recursive vs Iterative Factorial: Input Size vs Execution Time",
        "Input Size (n)", time_label, "factorial_time.png", 1000)
    add(factorial_df, "memory_usage", "Recursive vs Iterative Factorial: Input Size vs Memory Usage",
        "Input Size (n)", memory_label, "factorial_memory.png")

    add(loop_df, "execution_time", "Single Loop vs Nested Loop: Number of Iterations vs Execution Time",
        "Number of Iterations (n)", time_label, "loops_time.png", 1000)
    add(loop_df, "memory_usage", "Single Loop vs Nested Loop: Number of Iterations vs Memory Usage",
        "Number of Iterations (n)", memory_label, "loops_memory.png")

    return graphs


# ---------------------------------------------------------------------------
# Experimental analysis (everything here is computed from real results)
# ---------------------------------------------------------------------------
def estimate_growth_exponent(sizes, times):
    """
    Estimate k in  time ≈ c * n^k  using a straight-line fit on a log-log scale.
      k ≈ 0  -> constant / very slowly growing (e.g. O(log n))
      k ≈ 1  -> linear, O(n)
      k ≈ 2  -> quadratic, O(n²)
    Returns NaN if there are fewer than 2 usable points.
    """
    sizes = np.asarray(sizes, dtype=float)
    times = np.asarray(times, dtype=float)
    usable = (sizes > 0) & (times > 0)
    if usable.sum() < 2 or len(set(sizes[usable])) < 2:
        return float("nan")
    slope, _ = np.polyfit(np.log(sizes[usable]), np.log(times[usable]), 1)
    return float(slope)


def growth_class(exponent):
    """Turn an estimated exponent into one of: log, linear, quadratic, steeper."""
    if math.isnan(exponent):
        return "unknown"
    if exponent < 0.4:
        return "log"
    if exponent < 1.4:
        return "linear"
    if exponent < 2.5:
        return "quadratic"
    return "steeper"


GROWTH_TEXT = {
    "log": "almost constant / logarithmic growth",
    "linear": "roughly linear growth",
    "quadratic": "roughly quadratic growth",
    "steeper": "growth steeper than quadratic",
    "unknown": "not enough data",
}


def summarize_results(df):
    """
    Build a summary table (one row per algorithm) from a results DataFrame.
    Uses only rows with status "ok".
    """
    columns = ["algorithm", "smallest_size", "largest_size", "time_at_smallest",
               "time_at_largest", "size_growth", "time_growth", "growth_exponent",
               "observed_growth", "matches_theory", "memory_at_largest_kb",
               "comparisons_at_largest", "max_recursion_depth"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)

    good = df[df["status"] == "ok"]
    rows = []
    for name, group in good.groupby("algorithm", sort=False):
        group = group.sort_values("input_size")
        first, last = group.iloc[0], group.iloc[-1]
        exponent = estimate_growth_exponent(group["input_size"], group["execution_time"])
        observed = growth_class(exponent)
        expected = THEORETICAL_COMPLEXITY.get(name, {}).get("time_class")

        time_growth = float("nan")
        if first["execution_time"] > 0:
            time_growth = last["execution_time"] / first["execution_time"]
        size_growth = last["input_size"] / first["input_size"] if first["input_size"] > 0 else float("nan")

        rows.append({
            "algorithm": name,
            "smallest_size": int(first["input_size"]),
            "largest_size": int(last["input_size"]),
            "time_at_smallest": first["execution_time"],
            "time_at_largest": last["execution_time"],
            "size_growth": size_growth,
            "time_growth": time_growth,
            "growth_exponent": exponent,
            "observed_growth": GROWTH_TEXT[observed],
            "matches_theory": (observed == expected) if expected else None,
            "memory_at_largest_kb": last["memory_usage"],
            "comparisons_at_largest": last["comparisons"] if "comparisons" in group.columns else np.nan,
            "max_recursion_depth": last["max_recursion_depth"] if "max_recursion_depth" in group.columns else np.nan,
        })
    return pd.DataFrame(rows, columns=columns)


def build_observations(summary_df):
    """Write plain-English observations from a summary table (real numbers only)."""
    notes = []
    for _, r in summary_df.iterrows():
        text = (f"{r['algorithm']}: input grew from {r['smallest_size']} to {r['largest_size']} "
                f"(x{r['size_growth']:.0f}) and execution time grew x{r['time_growth']:.1f} "
                f"({format_time(r['time_at_smallest'])} -> {format_time(r['time_at_largest'])}). "
                f"Estimated exponent {r['growth_exponent']:.2f}, i.e. {r['observed_growth']}.")
        expected = THEORETICAL_COMPLEXITY.get(r["algorithm"], {})
        if r["matches_theory"] is True:
            text += " This is consistent with the theoretical time complexity."
        elif r["matches_theory"] is False:
            text += f" This differs from the theoretical {expected.get('average', '')} estimate"
            if "Factorial" in r["algorithm"]:
                text += (" - factorial values become huge integers, so each multiplication "
                         "costs more as n grows.")
            else:
                text += " - small inputs and timer noise can affect the estimate."
        if pd.notna(r["comparisons_at_largest"]):
            text += f" Comparisons at n={r['largest_size']}: {int(r['comparisons_at_largest'])}."
        if pd.notna(r["max_recursion_depth"]):
            text += f" Maximum recursion depth reached: {int(r['max_recursion_depth'])}."
        text += f" Peak extra memory at n={r['largest_size']}: {format_memory(r['memory_at_largest_kb'])}."
        notes.append(text)
    return notes


def build_complexity_table(*result_dataframes):
    """
    Theoretical complexity table + an 'Observed / Experimental Performance'
    column filled from whatever benchmark results are supplied.
    """
    frames = [d for d in result_dataframes if d is not None and not d.empty]
    summary = summarize_results(pd.concat(frames, ignore_index=True)) if frames else pd.DataFrame()
    summary_by_name = {r["algorithm"]: r for _, r in summary.iterrows()} if not summary.empty else {}

    rows = []
    for name, info in THEORETICAL_COMPLEXITY.items():
        if name in summary_by_name:
            s = summary_by_name[name]
            observed = (f"Exponent {s['growth_exponent']:.2f} ({s['observed_growth']}); "
                        f"time x{s['time_growth']:.1f} for input x{s['size_growth']:.0f}; "
                        f"memory {format_memory(s['memory_at_largest_kb'])} at n={s['largest_size']}")
        else:
            observed = "Run the benchmark to see observed results"
        rows.append({
            "Algorithm/Program": name,
            "Best Case": info["best"],
            "Average Case": info["average"],
            "Worst Case": info["worst"],
            "Space Complexity": info["space"],
            "Observed/Experimental Performance": observed,
        })
    return pd.DataFrame(rows)
