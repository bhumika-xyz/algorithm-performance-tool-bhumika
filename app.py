"""
app.py - Streamlit user interface for the
Algorithm Performance Measurement and Benchmarking Tool.

Run with:   streamlit run app.py
"""

import pandas as pd
import streamlit as st

import benchmark_engine as be
import code_benchmark as cb
import search_analysis as sa

st.set_page_config(page_title="Algorithm Benchmarking Tool", layout="wide")
st.title("Algorithm Performance Measurement and Benchmarking Tool")
st.caption("DAA Lab Assignment 2 - measure execution time and memory usage, "
           "then compare theoretical and experimental complexity.")


# ---------------------------------------------------------------------------
# Session state: keeps benchmark results while the user clicks around
# ---------------------------------------------------------------------------
for key in ("search_df", "factorial_df", "loop_df", "graphs"):
    if key not in st.session_state:
        st.session_state[key] = None


def parse_sizes(text):
    """Turn '100, 1000, 10000' into [100, 1000, 10000]. Raises ValueError if invalid."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not parts:
        raise ValueError("Enter at least one input size, e.g. 100, 1000, 10000")
    sizes = []
    for part in parts:
        if not part.isdigit():
            raise ValueError(f"'{part}' is not a valid size. Use positive whole numbers separated by commas.")
        sizes.append(int(part))
    return sizes


def show_run_metrics(seconds, memory_kb):
    """Show execution time and memory usage as two metric boxes."""
    c1, c2 = st.columns(2)
    c1.metric("Execution time", be.format_time(seconds))
    c2.metric("Memory usage (peak)", be.format_memory(memory_kb))


tab_search, tab_code, tab_auto, tab_viz, tab_complexity = st.tabs([
    "1. Search Algorithm Analysis",
    "2. Code Benchmarking",
    "3. Automated Benchmarking",
    "4. Performance Visualization",
    "5. Complexity Analysis",
])

# ---------------------------------------------------------------------------
# TAB 1 - Search Algorithm Analysis
# ---------------------------------------------------------------------------
with tab_search:
    st.header("Search Algorithm Analysis")
    left, right = st.columns(2)
    algorithm = left.selectbox("Algorithm", sa.SEARCH_ALGORITHMS)
    size = left.number_input("Dataset size (n)", min_value=0, max_value=sa.MAX_DATASET_SIZE,
                             value=1000, step=100)
    dataset_type = right.radio("Dataset type", ["Sorted", "Unsorted (random)"])
    search_key = right.number_input("Search key", value=500, step=1)
    st.caption("The sorted dataset contains the even numbers 0, 2, 4, ..., 2(n-1). "
               "Even keys are found; odd keys are not found.")

    if st.button("Run search"):
        try:
            info = sa.run_search(algorithm, int(size), int(search_key),
                                 sorted_data=(dataset_type == "Sorted"))
            if info["found"]:
                st.success(f"Key {info['key']} FOUND at index {info['index']}.")
            else:
                st.warning(f"Key {info['key']} was NOT found (index = -1).")
            st.metric("Number of comparisons", info["comparisons"])
            show_run_metrics(info["execution_time"], info["memory_usage"])
            st.caption(f"First elements of the dataset: {info['data_preview']}")
            theory = be.THEORETICAL_COMPLEXITY[algorithm]
            st.caption(f"Theory: worst-case time {theory['worst']}, space {theory['space']}.")
        except ValueError as error:
            st.error(str(error))

# ---------------------------------------------------------------------------
# TAB 2 - Code Benchmarking
# ---------------------------------------------------------------------------
with tab_code:
    st.header("Code Benchmarking")
    program = st.selectbox("Program", cb.PROGRAM_NAMES)
    limit = cb.MAX_INPUT[program]
    value = st.number_input(f"Input size / value (0 to {limit:,})", min_value=0,
                            max_value=limit, value=min(100, limit), step=1)

    if st.button("Run program"):
        try:
            with st.spinner("Running..."):
                info = cb.run_program(program, int(value))
            st.success(f"Result: {info['result']}")
            show_run_metrics(info["execution_time"], info["memory_usage"])
            if info["max_recursion_depth"] is not None:
                st.metric("Maximum recursion depth", info["max_recursion_depth"])
            theory = be.THEORETICAL_COMPLEXITY[program]
            st.caption(f"Theory: worst-case time {theory['worst']}, space {theory['space']}.")
        except ValueError as error:
            st.error(str(error))

# ---------------------------------------------------------------------------
# TAB 3 - Automated Benchmarking
# ---------------------------------------------------------------------------
with tab_auto:
    st.header("Automated Benchmarking")
    category = st.selectbox("Benchmark category", ["Search", "Factorial", "Loops", "All categories"])

    default_sizes = {"Search": sa.DEFAULT_SEARCH_SIZES, "Factorial": cb.DEFAULT_FACTORIAL_SIZES,
                     "Loops": cb.DEFAULT_LOOP_SIZES}
    sizes_text = None
    include_slow = False
    if category != "All categories":
        sizes_text = st.text_input("Input sizes (comma separated)",
                                   ", ".join(map(str, default_sizes[category])),
                                   key=f"sizes_{category}")
    if category in ("Loops", "All categories"):
        include_slow = st.checkbox(
            f"Also run Nested Loop for sizes above {cb.NESTED_LOOP_SAFE_LIMIT} "
            "(n = 10000 takes over a minute, n = 50000 hours)")
        st.caption(f"Without the tick, Nested Loop sizes above {cb.NESTED_LOOP_SAFE_LIMIT} "
                   "are shown as 'skipped' in the table.")

    if st.button("Run benchmark"):
        try:
            with st.spinner("Benchmarking... please wait."):
                if category in ("Search", "All categories"):
                    sizes = parse_sizes(sizes_text) if sizes_text else None
                    st.session_state.search_df = sa.run_search_benchmark(sizes, save=True)
                if category in ("Factorial", "All categories"):
                    sizes = parse_sizes(sizes_text) if sizes_text else None
                    st.session_state.factorial_df = cb.run_factorial_benchmark(sizes, save=True)
                if category in ("Loops", "All categories"):
                    sizes = parse_sizes(sizes_text) if sizes_text else None
                    st.session_state.loop_df = cb.run_loop_benchmark(sizes, include_slow=include_slow, save=True)
            st.session_state.graphs = None      # old graphs no longer match the data
            st.success("Benchmark finished. Results were saved as CSV files in the results/ folder.")
        except ValueError as error:
            st.error(str(error))

    shown = {"Search": [("Search results", "search_df", "search_benchmark.csv")],
             "Factorial": [("Factorial results", "factorial_df", "factorial_benchmark.csv")],
             "Loops": [("Loop results", "loop_df", "loop_benchmark.csv")]}
    shown["All categories"] = shown["Search"] + shown["Factorial"] + shown["Loops"]
    for label, state_key, csv_name in shown[category]:
        df = st.session_state[state_key]
        if df is not None:
            st.subheader(label)
            st.dataframe(df)
            st.caption("execution_time is in seconds, memory_usage is in KB.")
            st.download_button(f"Download {csv_name}", df.to_csv(index=False),
                               file_name=csv_name, mime="text/csv", key=f"dl_{state_key}")

# ---------------------------------------------------------------------------
# TAB 4 - Performance Visualization
# ---------------------------------------------------------------------------
with tab_viz:
    st.header("Performance Visualization")
    dfs = [st.session_state.search_df, st.session_state.factorial_df, st.session_state.loop_df]
    if all(d is None for d in dfs):
        st.info("No benchmark data yet. Go to the 'Automated Benchmarking' tab and run a benchmark first.")
    else:
        if st.button("Generate graphs"):
            try:
                st.session_state.graphs = be.generate_all_graphs(*dfs)
                st.success(f"Graphs saved as PNG files in {be.GRAPHS_DIR.name}/")
            except ValueError as error:
                st.error(str(error))

        if st.session_state.graphs:
            for title, path in st.session_state.graphs.items():
                st.image(str(path), caption=title)

        st.subheader("Observations from the benchmark data")
        for df in dfs:
            if df is not None:
                for note in be.build_observations(be.summarize_results(df)):
                    st.write("- " + note)
        skipped = [d[d["status"] != "ok"] for d in dfs if d is not None]
        skipped = pd.concat(skipped) if skipped else pd.DataFrame()
        if not skipped.empty:
            st.caption("Some runs were not completed (they are not plotted or analysed):")
            st.dataframe(skipped[["algorithm", "input_size", "status"]])

# ---------------------------------------------------------------------------
# TAB 5 - Complexity Analysis
# ---------------------------------------------------------------------------
with tab_complexity:
    st.header("Complexity Analysis")
    st.write("Theoretical complexities are fixed by the assignment. The last column is computed "
             "from your own benchmark results (empty until you run the benchmarks).")
    st.dataframe(be.build_complexity_table(st.session_state.search_df,
                                           st.session_state.factorial_df,
                                           st.session_state.loop_df))
    st.subheader("Time-space trade-offs (theory)")
    st.write("- Recursive Factorial uses O(n) space (one stack frame per call) while Iterative Factorial "
             "uses O(1) extra space; both take O(n) time.")
    st.write("- Binary Search is much faster than Linear Search on large data, but the data must be sorted first.")
    factorial_df = st.session_state.factorial_df
    if factorial_df is not None and "max_recursion_depth" in factorial_df.columns:
        depth = factorial_df["max_recursion_depth"].dropna()
        if not depth.empty:
            st.write(f"- In your benchmark, recursion reached a depth of {int(depth.max())} calls.")
