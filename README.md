# Algorithm Performance Measurement and Benchmarking Tool

BCA (AI & Data Science) - Semester V - Design and Analysis of Algorithms - Lab Assignment 2

## Purpose

A Python tool that runs algorithms/programs, measures their **execution time** and
**memory usage**, benchmarks them for many input sizes, draws graphs, and compares
**theoretical** complexity with **experimental** results.

## Features

- **Search analysis:** Linear Search and Binary Search (hand-written, with comparison counting)
- **Code benchmarking:** Single Loop, Nested Loop, Recursive Factorial, Iterative Factorial
- **Automated benchmarking:** reusable `BenchmarkEngine` -> pandas DataFrame -> CSV
- **Performance visualization:** matplotlib graphs saved as PNG files
- **Complexity analysis:** theoretical table + observations calculated from real benchmark data
- **Streamlit interface** with five tabs

## Technologies used

Python 3.11+ (recommended), Streamlit, pandas, NumPy, matplotlib, memory_profiler, Jupyter,
`time` and `tracemalloc` (standard library).

## Project structure

```
daa_lab2/
├── app.py                 Streamlit user interface
├── search_analysis.py     Linear Search, Binary Search, dataset generation
├── code_benchmark.py      Loops and factorial programs
├── benchmark_engine.py    BenchmarkEngine, measuring, graphs, analysis
├── project_notebook.ipynb Jupyter notebook demonstration
├── requirements.txt
├── README.md
├── .gitignore
├── graphs/                PNG graphs (created by the program)
├── screenshots/           Put your screenshots here
└── results/               CSV benchmark results (created by the program)
```

## Installation (Windows, VS Code terminal)

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

If PowerShell blocks activation, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use the Command Prompt instead.

## Running the application

```
streamlit run app.py
```

The app opens in your browser at http://localhost:8501.

## Running the individual modules

```
python search_analysis.py      # search demo + search benchmark (writes results/search_benchmark.csv)
python code_benchmark.py       # program demo + loop and factorial benchmarks
python benchmark_engine.py     # only defines the engine (prints nothing)
```

The notebook: open `project_notebook.ipynb` in VS Code, choose the `venv` kernel, and use **Run All**.

## Expected outputs

- **CSV files** in `results/`: `search_benchmark.csv`, `factorial_benchmark.csv`, `loop_benchmark.csv`
- **Graphs** in `graphs/`: `search_time.png`, `search_comparisons.png`, `search_memory.png`,
  `factorial_time.png`, `factorial_memory.png`, `loops_time.png`, `loops_memory.png`
- Times and memory values differ from computer to computer; the *shape* of the curves is what matters.

## Notes on measurement

- **Time:** average of several runs using `time.perf_counter()`.
- **Memory:** peak extra memory allocated during the call, measured with `tracemalloc`
  (in a separate run, because tracemalloc slows the code down). The input list is created
  before measuring, so it is not counted.
- **Nested Loop:** n = 50000 means 2.5 billion steps, so by default Nested Loop sizes above 2000
  are recorded as `skipped` (never invented). Tick the checkbox in the app (or use
  `include_slow=True`) to run them - expect very long waits.
- **Recursive Factorial:** the recursion limit is raised temporarily; inputs above 2000 are refused
  with a clear message (use Iterative Factorial instead).
